import { Component, Element, Host, State, h } from '@stencil/core';
import api from '../../api';
import type { SchoolYear } from '../../generated/api';
import { getSchoolYear } from '../../store';

var schoolYears: SchoolYear[] = [];

@Component({
  tag: 'lp-school-year-select-modal',
  shadow: true,
})
export class LpSchoolYearSelectModal {
  @Element() element: HTMLElement;
  @State() schoolYears: SchoolYear[] = schoolYears;
  @State() currentSchoolYear: SchoolYear;

  async componentWillLoad() {
    if (this.schoolYears.length === 0) api.schoolyearList().then(async res => schoolYears = this.schoolYears = await res.data);
    this.currentSchoolYear = await getSchoolYear();
  }

  render() {
    const modal = this.element.closest('ion-modal');
    return (
      <Host>
        <ion-header>
          <ion-toolbar>
            <ion-title>Vyberte školní rok</ion-title>
            <ion-buttons slot="end">
              <ion-button onclick={() => modal.dismiss(null, "close")} strong="true">&times;</ion-button>
            </ion-buttons>
          </ion-toolbar>
        </ion-header>
        <ion-content>
          <ion-list>
            <ion-radio-group value={this.currentSchoolYear.id}>
              {this.schoolYears.map(schoolYear => (
                <ion-item onclick={() => modal.dismiss(schoolYear, "done")}>
                  <ion-label>{schoolYear.name}</ion-label>
                  <ion-radio slot="end" value={schoolYear.id}></ion-radio>
                </ion-item>
              ))}
            </ion-radio-group>
          </ion-list>
        </ion-content>
      </Host>
    );
  }
}
