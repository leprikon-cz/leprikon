import { createStore } from "@stencil/store";
import api from "./api";
import { SchoolYear } from "./generated";

export interface LeprikonStore {
  currentSchoolYear?: SchoolYear;
}

const store = createStore<LeprikonStore>({});


/* Manage Shool Year */
let schoolYearLoading = false;

export const getSchoolYear = async (): Promise<SchoolYear> => {
  let currentSchoolYear = store.get("currentSchoolYear");
  if (currentSchoolYear) {
    return currentSchoolYear;
  }

  if (schoolYearLoading) {
    return new Promise(resolve => store.onChange("currentSchoolYear", resolve));
  } else {
    schoolYearLoading = true;
    // try local storage
    try {
      currentSchoolYear = JSON.parse(window.localStorage.getItem("leprikonSchoolYear")) as SchoolYear;
    } catch {}

    if (currentSchoolYear) store.set("currentSchoolYear", currentSchoolYear);

    // schedule update
    api.schoolyearCurrentRetrieve().then(async response => {
      const newSchoolYear = await response.data;
      if (currentSchoolYear?.id !== newSchoolYear.id) {
        store.set("currentSchoolYear", newSchoolYear);
      };
    });

    return currentSchoolYear || new Promise(resolve => store.onChange("currentSchoolYear", resolve));
  }
}
store.onChange("currentSchoolYear", schoolYear => window.localStorage.setItem("leprikonSchoolYear", JSON.stringify(schoolYear)));


export default store;
