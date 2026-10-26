import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs';
import { decode } from '../lib/game';

const base = 'http://127.0.0.1:3100';
const headers = { origin: base, 'x-expedition': '1' };

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
    await expect(page.locator('.treasure-strip')).toBeDisabled();
    await expect(page.getByRole('button', { name: /2\. Rừng Xoay Chữ/ })).toBeDisabled();
    for (let stage = 1; stage <= 5; stage++) {
      await expect(page.locator('.mission-top')).toContainText(`0${stage}`);
      await expect(page.getByLabel('MANH MỐI CỦA BẠN', { exact: true })).not.toHaveValue('');
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
  await page.getByRole('button', { name: 'Chuyến đi mới' }).click();
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
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    for (const theme of ['light', 'dark']) {
      const current = await page.locator('html').getAttribute('data-theme');
      if (current !== theme) await page.getByRole('button', { name: theme === 'dark' ? 'Bật giao diện tối' : 'Bật giao diện sáng' }).click();
      const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
      expect(result.violations, JSON.stringify(result.violations, null, 2)).toEqual([]);
      await page.screenshot({ path: `evidence/screenshots/${width}-${theme}.png`, fullPage: true });
    }
  }
  await page.keyboard.press('Tab');
  await page.getByRole('button', { name: 'Cách chơi', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(a11y.violations).toEqual([]);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Cách chơi', exact: true })).toBeFocused();
});
