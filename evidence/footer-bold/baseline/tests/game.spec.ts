import { expect, test, type Page, type Locator } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs';
import { decode } from '../lib/game';

const base = 'http://127.0.0.1:3100';
const headers = { origin: base, 'x-expedition': '1' };

async function expectPoppins(page: Page) {
  const result = await page.evaluate(async () => {
    const sample = 'CMC Infrasec Truy Tìm Kho Báu — ă â đ ê ô ơ ư';
    for (const weight of [400, 500, 600, 700, 800]) await document.fonts.load(`${weight} 16px Poppins`, sample);
    await document.fonts.ready;
    const loaded = [...document.fonts].some(face => face.family.includes('Poppins') && face.status === 'loaded');
    const wrong: string[] = [];
    const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node: Node | null;
    while ((node = walk.nextNode())) {
      const parent = node.parentElement;
      if (!parent || !node.textContent?.trim() || parent.closest('script,style,noscript,template') || !parent.getClientRects().length) continue;
      const style = getComputedStyle(parent);
      if (style.visibility === 'hidden' || style.display === 'none') continue;
      if (style.fontFamily.split(',')[0].replace(/["']/g, '').trim() !== 'Poppins') wrong.push(parent.tagName + ': ' + style.fontFamily);
    }
    return { loaded, wrong };
  });
  expect(result).toEqual({ loaded: true, wrong: [] });
  await page.evaluate(() => {
    const probe = document.createElement('span');
    probe.id = 'poppins-vietnamese-probe';
    probe.setAttribute('aria-hidden', 'true');
    probe.style.cssText = 'position:fixed;left:-10000px;top:0;font-family:Poppins;font-size:16px;';
    probe.textContent = String.fromCodePoint(...Array.from({ length: 90 }, (_, i) => 0x1EA0 + i)) + 'ĂăÂâĐđÊêÔôƠơƯư';
    document.body.append(probe);
  });
  const session = await page.context().newCDPSession(page);
  const proof: unknown[] = [];
  try {
    await session.send('DOM.enable'); await session.send('CSS.enable');
    const { root } = await session.send('DOM.getDocument');
    const { nodeId } = await session.send('DOM.querySelector', { nodeId: root.nodeId, selector: '#poppins-vietnamese-probe' });
    for (const weight of [400, 500, 600, 700, 800]) {
      await page.locator('#poppins-vietnamese-probe').evaluate((span, value) => { span.style.fontWeight = String(value); return span.getBoundingClientRect().width; }, weight);
      const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
      expect(fonts.length).toBeGreaterThan(0);
      expect(fonts.every(font => font.isCustomFont && /Poppins/i.test(font.familyName))).toBe(true);
      expect(fonts.reduce((n, font) => n + font.glyphCount, 0)).toBeGreaterThan(80);
      proof.push({ weight, fonts });
    }
    fs.writeFileSync('evidence/footer-cleanup/font-browser.json', JSON.stringify(proof, null, 2));
  } finally {
    await page.locator('#poppins-vietnamese-probe').evaluate(span => span.remove());
    await session.detach();
  }
}

async function expectOpaqueArtwork(logo: Locator) {
  const minimumAlpha = await logo.evaluate((image: HTMLImageElement) => {
    const canvas = document.createElement('canvas');
    canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
    const context = canvas.getContext('2d')!;
    context.drawImage(image, 0, 0);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    let minimum = 255;
    for (let i = 3; i < pixels.length; i += 4) minimum = Math.min(minimum, pixels[i]);
    return minimum;
  });
  expect(minimumAlpha).toBe(255);
}

test('all learning-bench methods and input errors', () => {
  expect(decode('SEVMTE8=', 'base64', 3, '')).toBe('HELLO');
  expect(decode('48454c4c4f', 'hex', 3, '')).toBe('HELLO');
  expect(decode('KHOOR 123{}', 'caesar', 3, '')).toBe('HELLO 123{}');
  expect(decode('<p>Hello</p><!-- note -->', 'inspect', 3, '')).toContain('<!-- note -->');
  expect(decode('FRAGMENT seq=2 text=LO\nFRAGMENT seq=1 text=HEL', 'log', 3, '')).toBe('HELLO');
  const blob = Buffer.from(Buffer.from('HELLO').map((v, i) => v ^ Buffer.from('SAO')[i % 3]));
  expect(decode(blob.toString('hex'), 'xor', 3, 'SAO')).toBe('HELLO');
  expect(decode(blob.toString('base64'), 'xor64', 3, 'SAO')).toBe('HELLO');
  for (const [input, tool] of [['', 'hex'], ['xyz', 'hex'], ['!', 'base64'], ['anything', 'log'], ['abcd', 'xor']]) {
    expect(() => decode(input, tool, 3, '')).toThrow();
  }
});
async function enter(page: Page, name = 'Captain Browser') {
  await page.goto('/');
  await page.getByLabel('Tên trên bảng xếp hạng').fill(name);
  await page.getByRole('button', { name: 'Bắt đầu thám hiểm', exact: true }).click();
  await expect(page.getByLabel('MANH MỐI CỦA BẠN', { exact: true })).toBeVisible();
}
function rotate(input: string, shift: number) {
  return input.replace(/[a-z]/gi, c => { const b = c <= 'Z' ? 65 : 97; return String.fromCharCode((c.charCodeAt(0) - b - shift + 26) % 26 + b); });
}
async function solveFromArtifact(page: Page, mode: string, stage: number) {
  const payload = await page.getByLabel('MANH MỐI CỦA BẠN', { exact: true }).inputValue();
  if (stage === 1) { const raw = Buffer.from(payload, 'base64').toString(); return mode === 'easy' ? raw : Buffer.from(raw, 'hex').toString(); }
  if (stage === 2) return rotate(payload, mode === 'easy' ? 3 : 7);
  if (stage === 3) return mode === 'easy' ? payload.match(/DAO\{[^}]+\}/)![0] : Buffer.from(payload.match(/data-cargo="([^"]+)"/)![1], 'base64').toString();
  if (stage === 4) {
    if (mode === 'easy') return [...payload.matchAll(/FRAGMENT seq=(\d+) text=([^\n]+)/g)].sort((a, b) => +a[1] - +b[1]).map(p => p[2]).join('');
    const response = await page.request.get('/api/v1/stages/4/artifact?mode=hard');
    expect(response.headers()['content-type']).toContain('image/png');
    const png = await response.body(); let comment = '';
    for (let offset = 8; offset < png.length;) {
      const length = png.readUInt32BE(offset), type = png.toString('ascii', offset + 4, offset + 8);
      const data = png.subarray(offset + 8, offset + 8 + length);
      if (type === 'tEXt' && data.toString().startsWith('Comment\0')) comment = data.subarray(8).toString();
      offset += length + 12;
    }
    expect(comment).not.toBe('');
    return Buffer.from(comment.split('|').sort().map(x => x.split(':')[1]).join(''), 'hex').toString();
  }
  const bytes = Buffer.from(payload, mode === 'easy' ? 'hex' : 'base64');
  const key = Buffer.from(mode === 'easy' ? 'SAO' : 'LA_BAN');
  return Buffer.from(bytes.map((b, i) => b ^ key[i % key.length])).toString();
}

for (const mode of ['easy', 'hard']) {
  test(`complete five-stage ${mode} journey, reward, restart and leaderboard`, async ({ page }) => {
    fs.mkdirSync('evidence/screenshots', { recursive: true });
    const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
    await enter(page, `Captain ${mode}`);
    if (mode === 'hard') await page.getByRole('button', { name: 'Hard Thử sức' }).click();
    if (mode === 'hard') await page.getByRole('button', { name: 'Bật giao diện tối' }).click();
    await expect(page.locator('.treasure-strip')).toBeDisabled();
    await expect(page.getByRole('button', { name: /2\. Rừng Xoay Chữ/ })).toBeDisabled();
    for (let stage = 1; stage <= 5; stage++) {
      await expect(page.locator('.mission-top')).toContainText(`0${stage}`);
      await expect(page.getByLabel('MANH MỐI CỦA BẠN', { exact: true })).not.toHaveValue('');
      await expect(page.getByLabel('MANH MỐI CỦA BẠN', { exact: true })).toHaveCSS('font-family', /Poppins/);
      if (stage === 1) {
        const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
        expect(a11y.violations).toEqual([]);
        await page.screenshot({ path: `evidence/screenshots/${mode}-playing.png`, fullPage: true });
      }
      if (stage === 1) {
        await page.getByLabel('Bạn tìm được flag nào?').fill('DAO{wrong}');
        await page.getByRole('button', { name: 'Kiểm tra flag', exact: true }).click();
        await expect(page.locator('.mission-panel').getByRole('alert')).toContainText('Chưa đúng');
      }
      const flag = await solveFromArtifact(page, mode, stage);
      if (mode === 'easy' && stage === 1) {
        await page.getByText('Bàn giải mã', { exact: true }).click();
        await page.getByRole('button', { name: 'Nạp ví dụ HELLO' }).click();
        await page.getByRole('button', { name: 'Giải mã', exact: true }).click();
        await expect(page.getByTestId('decoder-output')).toHaveText('HELLO');
        await page.getByRole('button', { name: 'Dùng manh mối', exact: true }).click();
        await page.getByRole('button', { name: 'Giải mã', exact: true }).click();
        await expect(page.getByTestId('decoder-output')).toHaveText(flag);
        await page.getByRole('button', { name: 'Điền vào ô flag' }).click();
      } else await page.getByLabel('Bạn tìm được flag nào?').fill(flag);
      await page.getByRole('button', { name: 'Kiểm tra flag', exact: true }).click();
      await expect(page.locator('.success')).toContainText('Đã tìm thấy mảnh la bàn');
      await page.getByRole('button', { name: stage === 5 ? 'Mở kho báu' : 'Đến địa điểm tiếp theo', exact: true }).click();
    }
    await expect(page.getByRole('dialog')).toContainText('sticker logo CMC Infrasec');
    await expect(page.getByTestId('reward-code')).toHaveText(/NF26-[A-F0-9]{12}/);
    const rewardLogo = page.getByTestId('club-logo-reward').locator('img:visible');
    await expect(rewardLogo).toHaveCount(1);
    await expect(rewardLogo).toHaveAttribute('src', new RegExp(mode === 'hard' ? 'club-logo.png' : 'club-logo-light.jpg'));
    await expect.poll(() => rewardLogo.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
    await expectOpaqueArtwork(rewardLogo);
    await expect(rewardLogo).toHaveCSS('object-fit', 'contain');
    await expect(rewardLogo).toHaveCSS('filter', 'none');
    await expect(page.getByTestId('club-logo-reward')).toHaveCSS('border-top-width', '0px');
    expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]);
    await page.screenshot({ path: `evidence/screenshots/${mode}-reward.png`, fullPage: true });
    const code = await page.getByTestId('reward-code').textContent();
    await page.getByRole('button', { name: 'Ghi dấu trên bảng xếp hạng' }).click();
    await expect(page.getByRole('table')).toContainText(`Captain ${mode}`);
    await expect(page.getByRole('table')).toContainText('3000');
    await page.getByRole('button', { name: 'Đóng', exact: true }).click();
    await page.reload();
    if (mode === 'hard') await page.getByRole('button', { name: 'Hard Thử sức' }).click();
    await page.locator('.treasure-strip').click();
    await expect(page.getByTestId('reward-code')).toHaveText(code!);
    expect(errors).toEqual([]);
  });
}

test('hints, download, journal, guide, replay and theme controls', async ({ page }) => {
  await enter(page);
  await page.getByRole('button', { name: /Cần một chút gợi ý/ }).click();
  await expect(page.locator('.hints ol li')).toHaveCount(1);
  const download = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Tải clue.txt' }).click();
  expect((await download).suggestedFilename()).toBe('clue.txt');
  await page.getByRole('button', { name: 'Cách chơi', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('CTF là');
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Nhật ký', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('Trang đầu vẫn còn trống');
  await page.getByRole('button', { name: 'Đóng', exact: true }).click();
  await page.getByRole('button', { name: 'Bật giao diện tối' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.getByText('Bàn giải mã', { exact: true }).click();
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]);
  await page.getByRole('button', { name: 'Chuyến đi mới' }).click();
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]);
  await page.getByRole('button', { name: 'Tạo chuyến mới' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.locator('.fragment-bar')).toContainText('0/5');
  await expect(page.locator('.hints ol li')).toHaveCount(0);
});

test('proxy origin, allowlist, body limits and session isolation', async ({ request }) => {
  expect((await request.post('/api/v1/session', { data: { name: 'Attacker' } })).status()).toBe(403);
  expect((await request.get('/api/v1/anything')).status()).toBe(404);
  expect((await request.post('/api/v1/session', { headers, data: 'x'.repeat(4097) })).status()).toBe(413);
  expect((await request.get('/api/v1/stages/1?mode=easy')).status()).toBe(401);
  const created = await request.post('/api/v1/session', { headers, data: { name: 'Proxy Captain' } });
  expect(created.status()).toBe(201);
  expect(created.headers()['set-cookie']).toMatch(/httponly/i);
  expect((await request.post('/api/v1/stages/1/hints?mode=easy', { headers, data: {} })).status()).toBe(403);
});

test('responsive light/dark, keyboard, accessibility and visual evidence', async ({ page }) => {
  fs.mkdirSync('evidence/screenshots', { recursive: true });
  for (const width of [320, 375, 414, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto('/');
    await expect(page.getByLabel('Tên trên bảng xếp hạng')).toBeVisible();
    await expectPoppins(page);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/CMC Infrasec\s*Truy Tìm Kho Báu/);
    await expect(page.locator('footer')).toHaveText("(c) CMC Infrasec x NextFest '26");
    await expect(page.locator('.below-map')).toHaveCount(0);
    await expect(page.getByText('Học bằng cách khám phá.', { exact: true })).toHaveCount(0);
    await expect(page.getByText('Mỗi màn là một kỹ năng, không phải bài kiểm tra.', { exact: true })).toHaveCount(0);
    await expect(page.locator('.footer-bottom')).toHaveCSS('justify-content', 'flex-start');
    await expect(page.locator('.footer-bottom')).toHaveCSS('text-align', 'left');
    await expect(page.locator('.footer-bottom')).toHaveCSS('font-size', width <= 600 ? '14px' : '16px');
    const footerEdges = await page.evaluate(() => ({
      footer: document.querySelector('.footer-bottom')!.getBoundingClientRect().left,
      text: document.querySelector('.footer-bottom > span')!.getBoundingClientRect().left,
      main: document.querySelector('.game-shell')!.getBoundingClientRect().left,
    }));
    expect(Math.abs(footerEdges.footer - footerEdges.text)).toBeLessThan(1);
    expect(Math.abs(footerEdges.main - footerEdges.footer)).toBeLessThan(1);
    await expect(page.locator('footer img')).toHaveCount(0);
    await expect(page.getByText('Weight ≤ 10', { exact: false })).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    for (const theme of ['light', 'dark']) {
      const current = await page.locator('html').getAttribute('data-theme');
      if (current !== theme) await page.getByRole('button', { name: theme === 'dark' ? 'Bật giao diện tối' : 'Bật giao diện sáng' }).click();
      const background = theme === 'light' ? 'rgb(254, 254, 254)' : 'rgb(2, 2, 2)';
      for (const selector of ['body', '.game-shell', '.map-panel']) {
        await expect(page.locator(selector)).toHaveCSS('background-color', background);
      }
      for (const placement of ['header']) {
        const logo = page.getByTestId(`club-logo-${placement}`).locator('img:visible');
        await expect(logo).toHaveCount(1);
        await expect(logo).toHaveAttribute('alt', 'Logo CMC Infrasec');
        await expect(logo).toHaveAttribute('src', new RegExp(theme === 'dark' ? 'club-logo.png' : 'club-logo-light.jpg'));
        await logo.scrollIntoViewIfNeeded();
        await expect.poll(() => logo.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
        await expectOpaqueArtwork(logo);
        await expect(logo).toHaveCSS('object-fit', 'contain');
        await expect(logo).toHaveCSS('filter', 'none');
        await expect(page.getByTestId(`club-logo-${placement}`)).toHaveCSS('border-top-width', '0px');
        expect(await logo.evaluate(img => Math.abs(img.getBoundingClientRect().width - img.getBoundingClientRect().height))).toBeLessThan(1);
      }
      await page.evaluate(() => scrollTo(0, 0));
      const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
      expect(result.violations, JSON.stringify(result.violations, null, 2)).toEqual([]);
      await page.screenshot({ path: `evidence/screenshots/${width}-${theme}.png`, fullPage: true });
    }
  }
  await page.keyboard.press('Tab');
  await page.getByRole('button', { name: 'Cách chơi', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  expect(await page.getByRole('dialog').evaluate(dialog => getComputedStyle(dialog, '::backdrop').backgroundColor)).toMatch(/^rgba\(0, 0, 0,/);
  const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(a11y.violations).toEqual([]);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Cách chơi', exact: true })).toBeFocused();
});

test('official logo assets are served and authorize the real reward artwork', async ({ request }) => {
  const catalog = await request.get('/api/v1/catalog');
  expect((await catalog.json()).logo_ready).toBe(true);
  for (const name of ['club-logo.png', 'club-logo-light.jpg']) {
    const response = await request.get('/' + name);
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toMatch(/^image\//);
    expect((await response.body()).length).toBeGreaterThan(10000);
  }
});
