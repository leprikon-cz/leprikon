import base64
import hashlib
import re
import secrets
import uuid
from datetime import datetime
from itertools import chain

from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.template.loader import get_template
from django.urls import reverse
from django.utils import translation
from django.utils.functional import cached_property
from django.utils.text import slugify
from pymongo import DESCENDING, MongoClient, UpdateMany, UpdateOne
from rocketchat_API.rocketchat import RocketChat as _RocketChat

from .conf import settings
from .models.leprikonsite import LeprikonSite
from .models.messages import Message
from .models.subjects import CHAT_GROUP_BROADCAST, Subject, SubjectRegistration

User = get_user_model()

http_re = re.compile("^http")

Leprikon = {"_id": "leprikon", "username": settings.LEPRIKON_CHAT_USERNAME}


def get_rc_url():
    return LeprikonSite.objects.get_current().url + "/_chat"


def get_rc_ws_url():
    return http_re.sub("ws", get_rc_url()) + "/websocket"


class QuerySet:
    def __init__(self, model, collection, query):
        self.model = model
        self._collection = collection
        self._query = query

    def _instance(self, doc):
        instance = self.model()
        instance.__dict__.update(doc)
        return instance

    def _get(self):
        obj = self._instance(self._collection.find_one(self._query))
        if not obj:
            raise self.model.DoesNotExist()
        return obj

    def _list(self):
        return [
            self._instance(doc)
            for doc in self._collection.find(self._query,).sort(
                "ts",
                DESCENDING,
            )
        ]

    def __getitem__(self, key):
        return self._list().__getitem__(key)

    def __len__(self):
        return self._collection.count_documents(self._query)

    def _clone(self):
        return QuerySet(self.model, self._collection, self._query.copy())

    def count(self):
        return len(self)

    def filter(self, **kwargs):
        qs = self._clone()
        qs._query.update(kwargs)
        return qs

    def get(self, **kwargs):
        return self.filter(**kwargs)._get()


def get_rc_config():
    ls = LeprikonSite.objects.get_current()
    return (
        ("Accounts_iframe_enabled", True),
        ("Accounts_iframe_url", reverse("leprikon:user_login")),
        ("Accounts_Iframe_api_method", "GET"),
        ("Accounts_Iframe_api_url", reverse("leprikon:api:rocketchat")),
        ("From_Email", settings.SERVER_EMAIL_PLAIN),
        ("Organization_Name", ls.name),
        ("Organization_Email", settings.SERVER_EMAIL_PLAIN),
        ("Organization_Type", "nonprofit"),
        ("Country", "czechRepublic"),
        ("Industry", "education"),
        ("Language", 9),  # TODO: configurable language
        ("Layout_Sidenav_Footer", ""),
        ("Livechat_enabled", True),
        ("Server_Type", "privateTeam"),
        ("Register_Server", False),
        ("SMTP_Host", settings.EMAIL_HOST),
        ("SMTP_Password", settings.EMAIL_HOST_PASSWORD),
        ("SMTP_Port", settings.EMAIL_PORT),
        ("SMTP_Username", settings.EMAIL_HOST_USER),
        ("Show_Setup_Wizard", "completed"),
        ("Site_Name", ls.name),
        ("Site_Url", get_rc_url()),
        ("Website", ls.url + "/"),
    )


def get_rc_default_home(ls=None):
    if ls is None:
        ls = LeprikonSite.objects.get_current()
    with translation.override(settings.LANGUAGE_CODE):
        return get_template("rocketchat/home.html").render(
            {
                "leprikon_site": ls,
            }
        )


rc_role_permissions = (
    (
        "user",
        (
            "create-c",
            "create-d",
            "create-p",
            "create-personal-access-tokens",
            "delete-own-message",
            "leave-c",
            "leave-p",
            "mention-all",
            "mention-here",
            "view-c-room",
            "view-d-room",
            "view-history",
            "view-p-room",
            "preview-c-room",
            "view-outside-room",
            "start-discussion",
            "start-discussion-other-user",
        ),
    ),
    (
        "guest",
        (
            "create-d",
            "create-personal-access-tokens",
            "delete-own-message",
            "view-d-room",
            "view-history",
            "view-joined-room",
            "view-p-room",
            "start-discussion",
        ),
    ),
)


def get_rc_id(obj):
    if isinstance(obj, Subject):
        return f"subject-{obj.id}"
    return f"{obj.__class__.__name__.lower()}-{obj.id}"


def get_rc_u(user):
    return {"_id": get_rc_id(user), "username": user.username}


def get_rc_leprikon_data():
    return {
        "_id": "leprikon",
        "name": settings.LEPRIKON_CHAT_NAME,
        "username": settings.LEPRIKON_CHAT_USERNAME,
        "emails": [
            {
                "address": settings.SERVER_EMAIL_PLAIN,
                "verified": True,
            }
        ],
        "active": True,
        "type": "user",
        "roles": ["admin"],
        "__insert": {
            "createdAt": datetime.now(),
        },
    }


def get_rc_user_data(user):
    return {
        "_id": get_rc_id(user),
        "createdAt": user.date_joined,
        "name": user.get_full_name(),
        "username": user.username,
        "emails": [{"address": user.email, "verified": True}],
        "active": user.is_active,
        "type": "user",
        "roles": ["admin", "livechat-agent"]
        if user.is_superuser
        else (["user", "livechat-agent"] if user.is_staff else ["guest"]),
        "lastLogin": user.last_login,
        "_updatedAt": datetime.now(),
    }


def get_value(document, key):
    parts = key.split(".", 1)
    value = document[parts[0]]
    return get_value(value, parts[1]) if len(parts) == 2 else value


def get_rc_subject_room_data(subject):
    fname = f"{subject} ({subject.id})"
    now = datetime.now()
    broadcast = (subject.chat_group_type or subject.subject_type.chat_group_type) == CHAT_GROUP_BROADCAST
    return {
        "_id": get_rc_id(subject),
        "name": slugify(fname.replace("/", "-")),
        "fname": fname,
        "t": "p",
        "ro": broadcast,
        "broadcast": broadcast,
        "sysMes": False,
        "default": False,
        "u": Leprikon,
        "_updatedAt": now,
        "customFields": {"leprikon": "subject"},
        "__insert": {
            "msgs": 0,
            "usersCount": 0,
            "encrypted": False,
            "ts": now,
        },
    }


def get_rc_subscription_data(room_data, user, alert, groupMentions, owner_ids=None):
    now = datetime.now()
    subscription_data = {
        "_id": f'{room_data["_id"]}-{get_rc_id(user)}',
        "rid": room_data["_id"],
        "name": room_data["name"],
        "fname": room_data["fname"],
        "t": room_data["t"],
        "u": get_rc_u(user),
        "customFields": {"leprikon": True},
        "_updatedAt": now,
        "__insert": {
            "alert": alert,
            "open": True,
            "ts": now,
            "ls": now,
            "unread": 0,
            "userMentions": 0,
            "groupMentions": groupMentions,
        },
    }
    if owner_ids:
        subscription_data["roles"] = ["owner"] if user.id in owner_ids else []
    return subscription_data


def get_rc_subject_subscriptions_data(room_data, subject):
    leader_users = {lu.user.id: lu.user for lu in subject.leaders.select_related("user")}
    return chain(
        get_rc_subscription_data(room_data, user, False, 0, leader_users)
        for user in set(
            chain(
                leader_users.values(),
                (r.user for r in subject.registrations.select_related("user")),
            )
        )
    )


def rc_logout(auth_token, user_id):
    return (
        _RocketChat(
            auth_token=auth_token,
            user_id=user_id,
            server_url=settings.ROCKETCHAT_API_URL,
        )
        .logout()
        .json()
    )


class RocketChat:

    # mongo related helpers
    _mongo_session = None
    _mongo_trx_level = 0

    def __enter__(self):
        if not self._mongo_trx_level:
            self._mongo_session = self._mongo_client.start_session().__enter__()
            self._mongo_trx = self._mongo_session.start_transaction().__enter__()
        self._mongo_trx_level += 1
        return self

    def __exit__(self, *exc):
        self._mongo_trx_level -= 1
        if not self._mongo_trx_level:
            self._mongo_trx.__exit__(*exc)
            self._mongo_session.__exit__(*exc)
            self._mongo_session = None

    @cached_property
    def _mongo_client(self):
        return MongoClient(settings.MONGO_URL)

    @cached_property
    def _mongo(self):
        return self._mongo_client.get_default_database()

    def _get_query(self, document):
        on_insert = document.pop("__insert", False)
        query = {"$set": document}
        if on_insert:
            query["$setOnInsert"] = on_insert
        return query

    def _sync_one(self, collection, document, keys=("_id",)):
        return (
            getattr(self._mongo, collection)
            .update_one(
                {key: get_value(document, key) for key in keys},
                self._get_query(document),
                session=self._mongo_session,
                upsert=True,
            )
            .raw_result
        )

    def _sync_many(self, collection, documents, keys=("_id",)):
        operations = [
            UpdateOne(
                {key: get_value(document, key) for key in keys},
                self._get_query(document),
                upsert=True,
            )
            for document in documents
        ]
        if operations:
            return (
                getattr(self._mongo, collection)
                .bulk_write(
                    operations,
                    session=self._mongo_session,
                )
                .bulk_api_result
            )

    # RC proxy
    @cached_property
    def rc(self):
        self.sync_leprikon_user()
        return _RocketChat(
            user_id="leprikon",
            auth_token=self.create_login_token("leprikon"),
            server_url=settings.ROCKETCHAT_API_URL,
        )

    # Leprikon RC API
    def configure(self):
        return self._mongo.rocketchat_settings.bulk_write(
            [UpdateOne({"_id": key}, {"$set": {"value": value, "blocked": True}}) for key, value in get_rc_config()]
            + [
                # One time settings
                UpdateOne(
                    {"_id": "Layout_Home_Body", "value": {"$regex": "Welcome to Rocket.Chat"}},
                    {"$set": {"value": get_rc_default_home()}},
                ),
            ],
            session=self._mongo_session,
        ).bulk_api_result

    def create_login_token(self, user_id):
        login_token = secrets.token_hex()
        h = hashlib.sha256()
        h.update(login_token.encode())
        hashed_token = base64.encodebytes(h.digest()).decode().strip()
        self._mongo.users.update_one(
            {"_id": user_id},
            {
                "$push": {
                    "services.resume.loginTokens": {
                        "when": datetime.now(),
                        "hashedToken": hashed_token,
                    }
                }
            },
            session=self._mongo_session,
        )
        return login_token

    def sync_leprikon_user(self):
        return self._sync_one("users", get_rc_leprikon_data())

    def sync_user(self, user):
        return self._sync_one("users", get_rc_user_data(user))

    def sync_users(self):
        return self._sync_many("users", map(get_rc_user_data, User.objects.iterator()))

    def sync_roles(self):
        return self._mongo.rocketchat_permissions.bulk_write(
            list(
                chain.from_iterable(
                    (
                        # add missing permissions
                        UpdateMany(
                            {
                                "_id": {"$in": permissions},
                                "roles": {"$ne": role},
                            },
                            {"$push": {"roles": role}},
                        ),
                        # remove other permissions
                        UpdateMany(
                            {
                                "_id": {"$nin": permissions},
                                "roles": role,
                            },
                            {"$pull": {"roles": role}},
                        ),
                    )
                    for role, permissions in rc_role_permissions
                )
            ),
            session=self._mongo_session,
        ).bulk_api_result

    def sync_subject(self, subject):
        room_data = get_rc_subject_room_data(subject)
        with self:
            return (
                self._sync_one("rocketchat_room", room_data),
                self._sync_many("rocketchat_subscription", get_rc_subject_subscriptions_data(room_data, subject)),
            )

    def sync_subjects(self):
        room_data_subjects = [
            (get_rc_subject_room_data(subject), subject)
            for subject in Subject.objects.select_related("subject_type").iterator()
        ]
        with self:
            return (
                self._sync_many("rocketchat_room", (rds[0] for rds in room_data_subjects)),
                self._sync_many(
                    "rocketchat_subscription",
                    chain.from_iterable(get_rc_subject_subscriptions_data(*rds) for rds in room_data_subjects),
                ),
            )

    def sync_subscription(self, registration):
        room_data = get_rc_subject_room_data(registration.subject)
        return self._sync_one(
            "rocketchat_subscription",
            get_rc_subscription_data(room_data, registration.user, False, 0),
        )

    def merge_users(self, source, target):
        source_id = get_rc_id(source)
        target_id = get_rc_id(target)
        target_u = get_rc_u(target)
        with self:
            # merge rocketchat_livechat_department_agents
            for department_agent in self._mongo.rocketchat_livechat_department_agents.find(
                {"agentId": source_id}, session=self._mongo_session
            ):
                self._mongo.rocketchat_livechat_department_agents.count_documents(
                    {
                        "agentId": target_id,
                        "departmentId": department_agent["departmentId"],
                    }
                ) or self._sync_one(
                    "rocketchat_livechat_department_agents",
                    {
                        "_id": department_agent["_id"],
                        "agentId": target_id,
                        "username": target.username,
                    },
                )
            # merge rocketchat_subscription
            for subscription in self._mongo.rocketchat_subscription.find(
                {"u._id": source_id}, session=self._mongo_session
            ):
                subscription["_id"] = f"""{subscription['rid']}-{target_u['_id']}"""
                subscription["u"] = target_u
                self._sync_one(
                    "rocketchat_subscription",
                    subscription,
                )
            # merge transfer messages and rooms
            for collection in (
                self._mongo.rocketchat_message,
                self._mongo.rocketchat_room,
            ):
                collection.update_many(
                    {"u._id": source_id},
                    {"$set": {"u._id": target_id}},
                    session=self._mongo_session,
                )

    def get_leprikon_private_rooms_queryset(self):
        return QuerySet(
            Message,
            self._mongo.rocketchat_room,
            {
                "t": "p",
                "customFields.leprikon": {"$in": ["subject", "broadcast"]},
            },
        )

    def get_broadcast_room_choices(self):
        return (
            (r["_id"], r["fname"])
            for r in self._mongo.rocketchat_room.find(
                {
                    "t": "p",
                    "broadcast": True,
                    "customFields.leprikon": "broadcast",
                },
                ("_id", "fname"),
            )
        )

    def subscribe_users_to_broadcast_room(self, rid, users):
        with self:
            room_data = self._mongo.rocketchat_room.find_one(
                {
                    "_id": rid,
                    "t": "p",
                    "broadcast": True,
                    "customFields.leprikon": "broadcast",
                },
                session=self._mongo_session,
            )
            self._sync_many(
                "rocketchat_subscription",
                (get_rc_subscription_data(room_data, user, True, 1) for user in users),
                keys=("rid", "u._id"),
            )
            self._sync_one(
                "rocketchat_room",
                {
                    "_id": rid,
                    "usersCount": self._mongo.rocketchat_subscription.count_documents({"rid": rid}),
                },
            )

    def create_broadcast_room(self, author, subject, text, recipients):
        with self:
            name = slugify(subject.replace("/", "-"))
            now = datetime.now()
            room_data = {
                "_id": uuid.uuid4().hex[:10],
                "name": name,
                "fname": subject,
                "t": "p",
                "ro": True,
                "sysMes": False,
                "default": False,
                "u": get_rc_u(author),
                "_updatedAt": now,
                "msgs": 1,
                "usersCount": 0,
                "customFields": {"leprikon": "broadcast"},
                "broadcast": True,
                "encrypted": False,
                "ts": now,
            }
            self._mongo.rocketchat_room.insert_one(room_data, session=self._mongo_session)
            self._mongo.rocketchat_message.insert_one(
                {
                    "_id": room_data["_id"],
                    "rid": room_data["_id"],
                    "msg": text,
                    "ts": room_data["ts"],
                    "u": room_data["u"],
                    "mentions": [
                        {
                            "_id": "all",
                            "username": "all",
                        }
                    ],
                    "channels": [],
                    "_updatedAt": now,
                },
                session=self._mongo_session,
            )
            self.subscribe_users_to_broadcast_room(room_data["_id"], recipients)


@receiver(post_save)
def rc_sync_object(instance, **kwargs):
    if isinstance(instance, User):
        RocketChat().sync_user(instance)
    elif isinstance(instance, Subject):
        RocketChat().sync_subject(instance)
    elif isinstance(instance, LeprikonSite):
        RocketChat().configure()
    elif isinstance(instance, SubjectRegistration):
        RocketChat().sync_subscription(instance)


@receiver(post_delete)
def rc_delete_object(instance, **kwargs):
    if isinstance(instance, User):
        RocketChat().rc.users_delete(get_rc_id(instance))
    elif isinstance(instance, Subject):
        RocketChat().rc.channels_delete(get_rc_id(instance))
