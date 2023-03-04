import { newSpecPage } from '@stencil/core/testing';
import { LpSchoolYearSelectModal } from '../lp-school-year-select-modal';

describe('lp-school-year-select-modal', () => {
  it('renders', async () => {
    const page = await newSpecPage({
      components: [LpSchoolYearSelectModal],
      html: `<lp-school-year-select-modal></lp-school-year-select-modal>`,
    });
    expect(page.root).toEqualHtml(`
      <lp-school-year-select-modal>
        <mock:shadow-root>
          <slot></slot>
        </mock:shadow-root>
      </lp-school-year-select-modal>
    `);
  });
});
