import { newSpecPage } from '@stencil/core/testing';
import { LpSchoolYear } from '../lp-school-year';

describe('lp-school-year', () => {
  it('renders', async () => {
    const page = await newSpecPage({
      components: [LpSchoolYear],
      html: `<lp-school-year></lp-school-year>`,
    });
    expect(page.root).toEqualHtml(`
      <lp-school-year>
        <mock:shadow-root>
          <slot></slot>
        </mock:shadow-root>
      </lp-school-year>
    `);
  });
});
