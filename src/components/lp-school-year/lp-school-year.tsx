import { Component, State } from '@stencil/core';
import type { SchoolYear } from '../../generated';
import store, { getSchoolYear } from '../../store';

@Component({tag: 'lp-school-year'})
export class LpSchoolYear {
  @State() currentSchoolYear?: SchoolYear;

  async componentWillLoad() {
    this.currentSchoolYear = await getSchoolYear();
    store.onChange("currentSchoolYear", newSchoolYear => this.currentSchoolYear = newSchoolYear);
  }

  render() {
    return this.currentSchoolYear.name;
  }
}
