import { newE2EPage } from '@stencil/core/testing';

describe('lp-school-year', () => {
  it('renders', async () => {
    const page = await newE2EPage();
    await page.setContent('<lp-school-year></lp-school-year>');

    const element = await page.find('lp-school-year');
    expect(element).toHaveClass('hydrated');
  });
});
