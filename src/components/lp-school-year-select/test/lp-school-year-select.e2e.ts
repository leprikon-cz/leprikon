import { newE2EPage } from '@stencil/core/testing';

describe('lp-school-year-select', () => {
  it('renders', async () => {
    const page = await newE2EPage();
    await page.setContent('<lp-school-year-select></lp-school-year-select>');

    const element = await page.find('lp-school-year-select');
    expect(element).toHaveClass('hydrated');
  });
});
