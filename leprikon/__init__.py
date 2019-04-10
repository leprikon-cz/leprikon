__version__ = '2.5.4'
default_app_config = 'leprikon.apps.LeprikonConfig'

staticfiles_urls = {
    # bootstrap (https://cdnjs.com/libraries/twitter-bootstrap)
    'leprikon/lib/bootstrap/css/bootstrap-grid.css': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/css/bootstrap-grid.css', 'sha256', 'cCazLItaM+Zz5UEzu9HNzlgWhXlvknCzjdE45LBeTns='),  # NOQA
    'leprikon/lib/bootstrap/css/bootstrap-grid.css.map': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/css/bootstrap-grid.css.map', 'sha256', '2MgjO0zpqYZscatQSGWJ9Io9U8EjvXk0iYygYz1Q+Ms='),  # NOQA
    'leprikon/lib/bootstrap/css/bootstrap-grid.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/css/bootstrap-grid.min.css', 'sha256', 'D9AvR0EzkNZoWZVSvI3ch+uf/Z5izrIpcbsykVphwPU='),  # NOQA
    'leprikon/lib/bootstrap/css/bootstrap-grid.min.css.map': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/css/bootstrap-grid.min.css.map', 'sha256', 'kZzlXLpTC0WvL0AL7nXf07BJ28WnY/1H/HrKgS68Q4I='),  # NOQA
    'leprikon/lib/bootstrap/css/bootstrap-reboot.css': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/css/bootstrap-reboot.css', 'sha256', 'Za8TaoAYg1BzmU9Re7Fiy6Hh3ac4jswPE1MKeTs95bw='),  # NOQA
    'leprikon/lib/bootstrap/css/bootstrap-reboot.css.map': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/css/bootstrap-reboot.css.map', 'sha256', '3e6awqXPijx918dzyzbbHKwaDBTsIQ8Us38QY30GRms='),  # NOQA
    'leprikon/lib/bootstrap/css/bootstrap-reboot.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/css/bootstrap-reboot.min.css', 'sha256', 'dARYuC3pd0wa/7R4Hkt/sR2zfLHCgbnVAQ2sPwhNe0A='),  # NOQA
    'leprikon/lib/bootstrap/css/bootstrap-reboot.min.css.map': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/css/bootstrap-reboot.min.css.map', 'sha256', 'dIm3VZXztwbIlhOzVt+ggg5Dvhp28MJQGJoweOH9cAE='),  # NOQA
    'leprikon/lib/bootstrap/css/bootstrap.css': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/css/bootstrap.css', 'sha256', 'Nfu23DiRqsrx/6B6vsI0T9vEVKq1M6KgO8+TV363g3s='),  # NOQA
    'leprikon/lib/bootstrap/css/bootstrap.css.map': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/css/bootstrap.css.map', 'sha256', 'CMAZj3JKoZUVYSxVPS/FeGatmYSvHkujo5oaZLNXx0o='),  # NOQA
    'leprikon/lib/bootstrap/css/bootstrap.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/css/bootstrap.min.css', 'sha256', 'YLGeXaapI0/5IgZopewRJcFXomhRMlYYjugPLSyNjTY='),  # NOQA
    'leprikon/lib/bootstrap/css/bootstrap.min.css.map': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/css/bootstrap.min.css.map', 'sha256', 'xMZ0SaSBYZSHVjFdZTAT/IjRExRIxSriWcJLcA9nkj0='),  # NOQA
    'leprikon/lib/bootstrap/js/bootstrap.bundle.js': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/js/bootstrap.bundle.js', 'sha256', 'pVreZ67fRaATygHF6T+gQtF1NI700W9kzeAivu6au9U='),  # NOQA
    'leprikon/lib/bootstrap/js/bootstrap.bundle.js.map': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/js/bootstrap.bundle.js.map', 'sha256', '3UpdqvoTc6M2sug8WtFhr/m3tg+4zLMgoMgjqpn5n1I='),  # NOQA
    'leprikon/lib/bootstrap/js/bootstrap.bundle.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/js/bootstrap.bundle.min.js', 'sha256', 'fzFFyH01cBVPYzl16KT40wqjhgPtq6FFUB6ckN2+GGw='),  # NOQA
    'leprikon/lib/bootstrap/js/bootstrap.bundle.min.js.map': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/js/bootstrap.bundle.min.js.map', 'sha256', '8i3JQdKYQQcJzmbkwhwY+1XPe7Utf1LdBnYZCvNmKWc='),  # NOQA
    'leprikon/lib/bootstrap/js/bootstrap.js': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/js/bootstrap.js', 'sha256', 'pl1bSrtlqtN/MCyW8XUTYuJCKohp9/iJESVW1344SBM='),  # NOQA
    'leprikon/lib/bootstrap/js/bootstrap.js.map': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/js/bootstrap.js.map', 'sha256', 'R81NA2DWe8EPjZ2OUhieXYgvvXBnm78oMdeqOtSEr7c='),  # NOQA
    'leprikon/lib/bootstrap/js/bootstrap.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/js/bootstrap.min.js', 'sha256', 'CjSoeELFOcH0/uxWu6mC/Vlrc1AARqbm/jiiImDGV3s='),  # NOQA
    'leprikon/lib/bootstrap/js/bootstrap.min.js.map': ('https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.3.1/js/bootstrap.min.js.map', 'sha256', 'vMfBbEXmojM9AaHrIyKSo+20n5JM7KMyJkBCfL4pgL4='),  # NOQA

    # jquery (https://cdnjs.com/libraries/jquery/)
    'leprikon/lib/jquery.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/jquery/3.4.1/jquery.min.js', 'sha256', 'CSXorXvZcTkaix6Yvo6HppcZGetbYMGWSFlBw8HfCJo='),  # NOQA

    # popper
    'leprikon/lib/popper.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.15.0/umd/popper.min.js', 'sha256', 'fTuUgtT7O2rqoImwjrhDgbXTKUwyxxujIMRIK7TbuNU='),  # NOQA

    # bootstrap-datetimepicker
    'leprikon/lib/bootstrap-datetimepicker/css/bootstrap-datetimepicker-standalone.css': ('https://cdnjs.cloudflare.com/ajax/libs/bootstrap-datetimepicker/4.17.47/css/bootstrap-datetimepicker-standalone.css', 'sha256', 'y/nn1YJAT/GwVsHZTooNErdWLjZvqMFJxNRLvigMD4I='),  # NOQA
    'leprikon/lib/bootstrap-datetimepicker/css/bootstrap-datetimepicker-standalone.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/bootstrap-datetimepicker/4.17.47/css/bootstrap-datetimepicker-standalone.min.css', 'sha256', 'SMGbWcp5wJOVXYlZJyAXqoVWaE/vgFA5xfrH3i/jVw0='),  # NOQA
    'leprikon/lib/bootstrap-datetimepicker/css/bootstrap-datetimepicker-standalone.min.css.map': ('https://cdnjs.cloudflare.com/ajax/libs/bootstrap-datetimepicker/4.17.47/css/bootstrap-datetimepicker-standalone.min.css.map', 'sha256', 'vITjuLQEPaTgktp5dx1uK3+lSnQReTi27m2jBO6fyNY='),  # NOQA
    'leprikon/lib/bootstrap-datetimepicker/css/bootstrap-datetimepicker.css': ('https://cdnjs.cloudflare.com/ajax/libs/bootstrap-datetimepicker/4.17.47/css/bootstrap-datetimepicker.css', 'sha256', 'b5ZKCi55IX+24Jqn638cP/q3Nb2nlx+MH/vMMqrId6k='),  # NOQA
    'leprikon/lib/bootstrap-datetimepicker/css/bootstrap-datetimepicker.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/bootstrap-datetimepicker/4.17.47/css/bootstrap-datetimepicker.min.css', 'sha256', 'yMjaV542P+q1RnH6XByCPDfUFhmOafWbeLPmqKh11zo='),  # NOQA
    'leprikon/lib/bootstrap-datetimepicker/js/bootstrap-datetimepicker.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/bootstrap-datetimepicker/4.17.47/js/bootstrap-datetimepicker.min.js', 'sha256', '5YmaxAwMjIpMrVlK84Y/+NjCpKnFYa8bWWBbUHSBGfU='),  # NOQA

    # bootstrap-multiselect
    'leprikon/lib/bootstrap-multiselect/css/bootstrap-multiselect.css': ('https://raw.githubusercontent.com/adeeb1/bootstrap-multiselect/support-bootstrap-4/dist/css/bootstrap-multiselect.css', 'sha256', 'LixSlwPPwaoPlhBo2/VoLiMNfSdigrCS4c7hVqt9gv8='),  # NOQA
    'leprikon/lib/bootstrap-multiselect/js/bootstrap-multiselect.js': ('https://raw.githubusercontent.com/adeeb1/bootstrap-multiselect/support-bootstrap-4/dist/js/bootstrap-multiselect.js', 'sha256', 'F1PyuyC8NFQrwP/q7dLwwaqw+GPzOmAqC7cKjptxNiU='),  # NOQA

    # bootstrap-social
    'leprikon/lib/bootstrap-social/bootstrap-social.css': ('https://cdnjs.cloudflare.com/ajax/libs/bootstrap-social/5.1.1/bootstrap-social.css', 'sha256', 'rnmbX+ZXZml9xbNUKt/qXfgpCi6zLJX7qqR+7vX/1ZY='),  # NOQA
    'leprikon/lib/bootstrap-social/bootstrap-social.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/bootstrap-social/5.1.1/bootstrap-social.min.css', 'sha256', 'rFMLRbqAytD9ic/37Rnzr2Ycy/RlpxE5QH52h7VoIZo='),  # NOQA
    'leprikon/lib/bootstrap-social/bootstrap-social.min.css.map': ('https://cdnjs.cloudflare.com/ajax/libs/bootstrap-social/5.1.1/bootstrap-social.min.css.map', 'sha256', 'C/r6vTyA2Y/sAPcmDebeXoWYy5fbTPkqxE4m3FM7T2E='),  # NOQA

    # ekko-lightbox
    'leprikon/lib/ekko-lightbox/ekko-lightbox.css': ('https://cdnjs.cloudflare.com/ajax/libs/ekko-lightbox/5.3.0/ekko-lightbox.css', 'sha256', 'HAaDW5o2+LelybUhfuk0Zh2Vdk8Y2W2UeKmbaXhalfA='),  # NOQA
    'leprikon/lib/ekko-lightbox/ekko-lightbox.js': ('https://cdnjs.cloudflare.com/ajax/libs/ekko-lightbox/5.3.0/ekko-lightbox.js', 'sha256', 'jGAkJO3hvqIDc4nIY1sfh/FPbV+UK+1N+xJJg6zzr7A='),  # NOQA
    'leprikon/lib/ekko-lightbox/ekko-lightbox.js.map': ('https://cdnjs.cloudflare.com/ajax/libs/ekko-lightbox/5.3.0/ekko-lightbox.js.map', 'sha256', 'BCi8N5Tq5TLpkh95lY0+tk4QBWVw/x3uZNYpea6q3dg='),  # NOQA
    'leprikon/lib/ekko-lightbox/ekko-lightbox.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/ekko-lightbox/5.3.0/ekko-lightbox.min.js', 'sha256', 'Y1rRlwTzT5K5hhCBfAFWABD4cU13QGuRN6P5apfWzVs='),  # NOQA
    'leprikon/lib/ekko-lightbox/ekko-lightbox.min.js.map': ('https://cdnjs.cloudflare.com/ajax/libs/ekko-lightbox/5.3.0/ekko-lightbox.min.js.map', 'sha256', 'YX7u2MMo0SzWrDmm+NBiBrIO/AaKyL6C91jhFAzBOeE='),  # NOQA

    # moment.js
    'leprikon/lib/moment-with-locales.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.24.0/moment-with-locales.min.js', 'sha256', 'AdQN98MVZs44Eq2yTwtoKufhnU+uZ7v2kXnD5vqzZVo='),  # NOQA

    # font-awesome
    'leprikon/lib/font-awesome/css/all.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/all.css', 'sha256', 'piqEf7Ap7CMps8krDQsSOTZgF+MU/0MPyPW2enj5I40='),  # NOQA
    'leprikon/lib/font-awesome/css/all.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/all.min.css', 'sha256', 'zmfNZmXoNWBMemUOo1XUGFfc0ihGGLYdgtJS3KCr/l0='),  # NOQA
    'leprikon/lib/font-awesome/css/brands.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/brands.css', 'sha256', 'PwdvTd8E3lKRgi536Ad8m9b6arU30QxuaQpWUn75Dcs='),  # NOQA
    'leprikon/lib/font-awesome/css/brands.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/brands.min.css', 'sha256', 'uDPmT0cBhgbD0vyb8hr076ZhG5XwUmJe/KCLiAvPyAo='),  # NOQA
    'leprikon/lib/font-awesome/css/fontawesome.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/fontawesome.css', 'sha256', 'aDHSB5J+Ds5b5qBm7+T5EXYKG+Xapm4c/46meCzQ+pE='),  # NOQA
    'leprikon/lib/font-awesome/css/fontawesome.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/fontawesome.min.css', 'sha256', '0mlw4Ae1j9eDzZTzLuw5X9fBCL9nAehrtVyKfIstZQA='),  # NOQA
    'leprikon/lib/font-awesome/css/regular.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/regular.css', 'sha256', '+JUKnbNzHAnEzOX0dnqmjzjMiI1m/pl5/UR7K/rPdus='),  # NOQA
    'leprikon/lib/font-awesome/css/regular.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/regular.min.css', 'sha256', 'ebp2xT462h5/AE9WxJwZea5WDAnZae3e4J0YFucWcbg='),  # NOQA
    'leprikon/lib/font-awesome/css/solid.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/solid.css', 'sha256', 'gpZL4O9v1sMxFqxDr+1zEsM5geg+qckpVQcMMEWIuRw='),  # NOQA
    'leprikon/lib/font-awesome/css/solid.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/solid.min.css', 'sha256', 'xlh4aT8Ni/MnbIvFWbnIrJ+YKe+1S/y1xNQl7YWArXc='),  # NOQA
    'leprikon/lib/font-awesome/css/svg-with-js.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/svg-with-js.css', 'sha256', 'l9rZNqoJt6EQFsHSLZ05b27pSEUjctrXZNW/2ml1dv8='),  # NOQA
    'leprikon/lib/font-awesome/css/svg-with-js.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/svg-with-js.min.css', 'sha256', 'KvRcHp28THFgp86ARBiw8Hy92AVvVzoaQ3DEJawiBME='),  # NOQA
    'leprikon/lib/font-awesome/css/v4-shims.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/v4-shims.css', 'sha256', 'dRsB5EBF7ZbkKjvkVsZ+v+WIFJS8cpuFHKgs8IHW8Hg='),  # NOQA
    'leprikon/lib/font-awesome/css/v4-shims.min.css': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/css/v4-shims.min.css', 'sha256', 'aHZRnvSsxGjbzQYQxIPzq+cU+R1DrVwWhl1Y2vJmMk8='),  # NOQA
    'leprikon/lib/font-awesome/js/all.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/all.js', 'sha256', '3++upIdscYTh7JbNFOC/2ubJySRGby0CV4wGGfUPY6c='),  # NOQA
    'leprikon/lib/font-awesome/js/all.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/all.min.js', 'sha256', 'iZGp5HAiwRmkbOKVYv5FUER4iXp5QbiEudkZOdwLrjw='),  # NOQA
    'leprikon/lib/font-awesome/js/brands.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/brands.js', 'sha256', 'N8Ka7ljKkCqmu5Z8EwzvNHJw59lRBCUl4YixJ3DXveI='),  # NOQA
    'leprikon/lib/font-awesome/js/brands.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/brands.min.js', 'sha256', 'WbG2UINZEMlkqWLXqYLGo/DAhCYbb7h5do/UWlsrHjU='),  # NOQA
    'leprikon/lib/font-awesome/js/conflict-detection.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/conflict-detection.js', 'sha256', 'orYc5xgyqZgm4hmqrf4QwS8P7LID/TZCznP6NRVT9cg='),  # NOQA
    'leprikon/lib/font-awesome/js/conflict-detection.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/conflict-detection.min.js', 'sha256', 'kAp/Y142Ro35sPIh/e3owJ+P4X07EM8e4mXmybzd7n4='),  # NOQA
    'leprikon/lib/font-awesome/js/fontawesome.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/fontawesome.js', 'sha256', 'aP5ofYMzqlPZyAK28ldd3h9D6ZWwb9jjoC34BdE682E='),  # NOQA
    'leprikon/lib/font-awesome/js/fontawesome.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/fontawesome.min.js', 'sha256', 'jKgZ4tWXHoVO7xN6gxmgTojfB+Xt/hbhPJuyNlZ00Hc='),  # NOQA
    'leprikon/lib/font-awesome/js/regular.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/regular.js', 'sha256', 'pG4EHeQSXPJ+EOJH0v3Ayqdy74azckwA3gMAg7835yU='),  # NOQA
    'leprikon/lib/font-awesome/js/regular.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/regular.min.js', 'sha256', 'aog1jyK3Wyksx1H0gL43JSTnqUttwb/D3uYd1xwjfpc='),  # NOQA
    'leprikon/lib/font-awesome/js/solid.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/solid.js', 'sha256', 'rfUkhqkLBQjEOyhgoEiz2uPTCNnFtwpDNp74Zc8e6XU='),  # NOQA
    'leprikon/lib/font-awesome/js/solid.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/solid.min.js', 'sha256', 'DI44KiLwZRa9TvJbz6PCDshHJ+/0bIkBoIMa0cnFPl8='),  # NOQA
    'leprikon/lib/font-awesome/js/v4-shims.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/v4-shims.js', 'sha256', 'qHn89YJmUl5fy7V9p2oECnikuTpugag9StYr6lbPh4Q='),  # NOQA
    'leprikon/lib/font-awesome/js/v4-shims.min.js': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/js/v4-shims.min.js', 'sha256', 'aImy7q1L7Eilux5fG2zpA9rS6nYvKQ0HvogJH33L2ts='),  # NOQA
    'leprikon/lib/font-awesome/sprites/brands.svg': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/sprites/brands.svg', 'sha256', 'ofQpDoCWA1j+jEpfKpjeeLaqmr2hxiAiJPouVMKL2gs='),  # NOQA
    'leprikon/lib/font-awesome/sprites/regular.svg': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/sprites/regular.svg', 'sha256', 'JWQRu1LiW1q0mXyyKV4HQHo9ITlmU8jmCWzx3L0iKAk='),  # NOQA
    'leprikon/lib/font-awesome/sprites/solid.svg': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/sprites/solid.svg', 'sha256', 'a3d2Xe7lJP5XVtFLbzWmRqjEZ1Efz77HT7o9joVDby8='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-brands-400.eot': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-brands-400.eot', 'sha256', 'cLarDietbBEMvIkcyjqnwg1mtaGPeFXdTnIDGHloYpE='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-brands-400.svg': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-brands-400.svg', 'sha256', 'o3jiOhnEfP8+zqY/rTqeXs+DOQE0eMKPhpXL7LGbNVQ='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-brands-400.ttf': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-brands-400.ttf', 'sha256', 'f8iCldu4M3/PhMDU/sgV4I9ooi8ZNGuToEVc5EeWswc='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-brands-400.woff': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-brands-400.woff', 'sha256', 'StiOajLbUaQc/xdBlwypWz5DP7+4viaccviBpC8riMY='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-brands-400.woff2': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-brands-400.woff2', 'sha256', 'l1cUxstwuhBb+ofSQV3y/d3kpGwdOrnQz0VGXlbLqX0='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-regular-400.eot': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-regular-400.eot', 'sha256', 'UEvATZ9ImUT1gT/vRKnzbowVp/shGzJUQEbq79+Tv3s='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-regular-400.svg': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-regular-400.svg', 'sha256', 'sVs0Zok2vraLZNvg6Brdmw26bKPt2m3EzBVu6ockVyA='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-regular-400.ttf': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-regular-400.ttf', 'sha256', 'BtY2aXH5EVdDM11Pbv852UJDvwcdRKqZbEWuWDiL43Y='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-regular-400.woff': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-regular-400.woff', 'sha256', 'pnjCQrNbAUxusmqCSloWAsAw2G2HH5b1k/MYrDhI1Sw='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-regular-400.woff2': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-regular-400.woff2', 'sha256', 'TAYaMC06rYDl0Ep2CPIKJstsqZXz42v7ZVAOF1Ut6+s='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-solid-900.eot': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-solid-900.eot', 'sha256', 'XyO3L9HapBktzJv3Q+6bMPuXL+Z5eQRN3yFstvYBmQo='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-solid-900.svg': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-solid-900.svg', 'sha256', 'yikykcrgLowv54EcvOOX5VWCLDfZCl23PK9YuejHQL4='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-solid-900.ttf': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-solid-900.ttf', 'sha256', 'ttt3U2PJzXRct4nWfDuz5HL1Xu56tG329HmObJy/SfQ='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-solid-900.woff': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-solid-900.woff', 'sha256', 'ALymqScbXhy7OWWnT0jBzgtyvL8IeQqiyrlfjcU2IVM='),  # NOQA
    'leprikon/lib/font-awesome/webfonts/fa-solid-900.woff2': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.2/webfonts/fa-solid-900.woff2', 'sha256', 'gP6Qy1WVOBWLwjX05TnZvK4gPhn6t8aXCq03sBVDSP8='),  # NOQA
}
