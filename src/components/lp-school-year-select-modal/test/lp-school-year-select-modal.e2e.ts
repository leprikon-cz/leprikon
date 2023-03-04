import { newE2EPage } from '@stencil/core/testing';

describe('lp-school-year-select-modal', () => {
  it('renders', async () => {
    const page = await newE2EPage();
    await page.setContent('<lp-school-year-select-modal></lp-school-year-select-modal>');

    const element = await page.find('lp-school-year-select-modal');
    expect(element).toHaveClass('hydrated');
  });
});
