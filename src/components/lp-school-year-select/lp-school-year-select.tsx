import { modalController } from '@ionic/core';
import { Component, Host, h } from '@stencil/core';
import api from '../../api';
import store from '../../store';

@Component({tag: 'lp-school-year-select'})
export class LpSchoolYearSelect {
  async openModal() {
    const modal = await modalController.create({component: "lp-school-year-select-modal"});
    modal.present();
    const result = await modal.onWillDismiss();
    if (result.role === "done") {
      await api.schoolyearCurrentCreate({id: result.data.id});
      store.set("currentSchoolYear", result.data);
    }
  }

  render() {
    return <Host onClick={this.openModal}><slot/></Host>;
  }
}
