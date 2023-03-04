import { newSpecPage } from '@stencil/core/testing';
import { LpSchoolYearSelect } from '../lp-school-year-select';

describe('lp-school-year-select', () => {
  it('renders', async () => {
    const page = await newSpecPage({
      components: [LpSchoolYearSelect],
      html: `<lp-school-year-select></lp-school-year-select>`,
    });
    expect(page.root).toEqualHtml(`
      <lp-school-year-select>
        <mock:shadow-root>
          <slot></slot>
        </mock:shadow-root>
      </lp-school-year-select>
    `);
  });
});
