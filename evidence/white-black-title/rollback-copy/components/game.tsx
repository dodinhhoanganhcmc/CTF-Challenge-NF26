'use client';

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { ArrowRightIcon, ArrowDownIcon, CompassIcon, MapTrifoldIcon, FlagIcon, LockKeyIcon, CheckIcon, TreasureChestIcon, FlaskIcon, TreeIcon, BinocularsIcon, LighthouseIcon, MountainsIcon, SunIcon, MoonIcon, BookOpenIcon, TrophyIcon, XIcon, DownloadSimpleIcon, LightbulbIcon, CopyIcon, SparkleIcon, CircleNotchIcon, ArrowCounterClockwiseIcon } from '@phosphor-icons/react';
import { api, decode, message, type Clue, type Entry, type Mode, type Reward, type Session, type Stage } from '@/lib/game';
import ClubLogo from '@/components/club-logo';

const icons = [FlaskIcon, TreeIcon, BinocularsIcon, LighthouseIcon, MountainsIcon];
const positions = [{ left: '15%', top: '66%' }, { left: '34%', top: '33%' }, { left: '53%', top: '62%' }, { left: '72%', top: '29%' }, { left: '87%', top: '60%' }];
const fallback: Stage[] = [
  { id: 1, title: 'Chai thư trôi dạt', location: 'Bãi Khởi Hành', category: 'Encoding', weight: 2, summary: 'Đọc lá thư đầu tiên.' },
  { id: 2, title: 'La bàn xoay chữ', location: 'Rừng Xoay Chữ', category: 'Crypto', weight: 4, summary: 'Xoay chữ để tìm hướng đi.' },
  { id: 3, title: 'Bí mật đài quan sát', location: 'Đài Quan Sát', category: 'Web', weight: 6, summary: 'Nhìn dưới bề mặt.' },
  { id: 4, title: 'Dấu vết ngọn hải đăng', location: 'Hải Đăng Ký Ức', category: 'Forensics', weight: 8, summary: 'Ghép những dấu vết còn lại.' },
  { id: 5, title: 'Cánh cửa cuối cùng', location: 'Hang Kho Báu', category: 'Crypto + Misc', weight: 10, summary: 'Dùng chìa khóa của bạn.' },
];
type Panel = 'guide' | 'journal' | 'leaderboard' | 'replay' | 'treasure' | null;

function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const dialog = ref.current;
    dialog?.showModal();
    return () => { dialog?.close(); previous?.focus(); };
  }, []);
  return <dialog ref={ref} className="modal" onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose(); }} aria-labelledby="dialog-title">
    <div className="modal-heading"><h2 id="dialog-title">{title}</h2><button className="icon-button" onClick={onClose} aria-label="Đóng"><XIcon size={22} /></button></div>
    {children}
  </dialog>;
}

function Bench({ clue, useResult }: { clue: Clue; useResult: (s: string) => void }) {
  const [tool, setTool] = useState(clue.tool);
  const [input, setInput] = useState('');
  const [key, setKey] = useState('');
  const [shift, setShift] = useState(3);
  const [output, setOutput] = useState('');
  const [error, setError] = useState('');
  function run() { try { setOutput(decode(input, tool, shift, key)); setError(''); } catch (e) { setOutput(''); setError(message(e)); } }
  return <details className="bench" open={false}>
    <summary><span><FlaskIcon size={19} /> Bàn giải mã</span><span className="small">Công cụ học tập <ArrowDownIcon /></span></summary>
    <div className="bench-body">
      <p className="small">Thử với ví dụ trước, rồi áp dụng cho manh mối của bạn. Dữ liệu được xử lý ngay trong trình duyệt.</p>
      <label htmlFor="decoder">Phương pháp</label>
      <select id="decoder" value={tool} onChange={e => { setTool(e.target.value); setOutput(''); setError(''); }}>
        <option value="base64">Base64 → văn bản</option><option value="hex">Hex → văn bản</option>
        <option value="caesar">Caesar · dịch lùi</option><option value="inspect">Đọc mã HTML</option>
        <option value="log">Ghép log theo seq</option><option value="xor">XOR từ hex</option><option value="xor64">XOR từ Base64</option>
      </select>
      {tool === 'caesar' && <><label htmlFor="shift">Số nấc dịch lùi</label><input id="shift" type="number" min="0" max="25" value={shift} onChange={e => setShift(Number(e.target.value))} /></>}
      {tool.startsWith('xor') && <><label htmlFor="xor-key">Khóa XOR</label><input id="xor-key" maxLength={100} value={key} onChange={e => setKey(e.target.value)} placeholder="Khóa từ hải đăng" /></>}
      <label htmlFor="decoder-input">Dữ liệu cần giải</label>
      <textarea id="decoder-input" value={input} maxLength={20000} onChange={e => setInput(e.target.value)} placeholder="Dán dữ liệu vào đây…" spellCheck={false} rows={4} />
      <div className="button-row"><button className="button secondary small-button" onClick={() => { setTool(clue.tool); setInput(clue.sample); setOutput(''); setError(''); }}>Nạp ví dụ HELLO</button>
        <button className="button secondary small-button" onClick={() => { setInput(clue.payload); setOutput(''); setError(''); }}>Dùng manh mối</button>
        <button className="button small-button" onClick={run}>Giải mã <ArrowRightIcon /></button></div>
      {error && <p role="alert" className="error">{error}</p>}
      {output && <div className="decoder-result"><span className="eyebrow">KẾT QUẢ</span><pre data-testid="decoder-output">{output}</pre>
        <div className="button-row"><button className="text-button" onClick={() => { setInput(output); setOutput(''); }}>Dùng cho lớp tiếp theo <ArrowRightIcon /></button>
          {output.startsWith('DAO{') && <button className="button secondary small-button" onClick={() => useResult(output)}>Điền vào ô flag</button>}</div></div>}
    </div>
  </details>;
}

export default function Game() {
  const [stages, setStages] = useState(fallback);
  const [guest, setGuest] = useState<Session | null>(null);
  const [name, setName] = useState('');
  const [mode, setMode] = useState<Mode>('easy');
  const [selected, setSelected] = useState(1);
  const [clue, setClue] = useState<(Clue & { mode: Mode }) | null>(null);
  const [flag, setFlag] = useState('');
  const [error, setError] = useState('');
  const [stageError, setStageError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  const [panel, setPanel] = useState<Panel>(null);
  const [dark, setDark] = useState(false);
  const [reward, setReward] = useState<Reward | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [boardTotal, setBoardTotal] = useState(0);
  const [boardOffset, setBoardOffset] = useState(0);
  const [panelError, setPanelError] = useState('');
  const [panelLoading, setPanelLoading] = useState(false);
  const [copied, setCopied] = useState('');
  const progress = guest?.modes[mode];
  const solved = progress?.solved || [];
  const current = Math.min(5, solved.length + 1);
  const isSolved = solved.includes(selected);
  const missionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const theme = localStorage.getItem('island-theme') === 'dark';
    setDark(theme); document.documentElement.dataset.theme = theme ? 'dark' : 'light';
    let active = true;
    Promise.all([
      api<{ stages: Stage[] }>('catalog').then(data => { if (active) setStages(data.stages); }),
      api<Session>('session').then(data => {
        if (active) { setGuest(data); setSelected(Math.min(5, data.modes.easy.solved.length + 1)); }
      }).catch(e => { if ((e as { status?: number }).status !== 401) throw e; }),
    ]).catch(e => { if (active) setError(message(e)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [retry]);

  useEffect(() => {
    setClue(null); setStageError(''); setFlag(''); setFeedback('');
    if (!guest) return;
    const controller = new AbortController();
    api<Clue>(`stages/${selected}?mode=${mode}`, undefined, undefined, controller.signal)
      .then(data => setClue({ ...data, mode })).catch(e => { if (!controller.signal.aborted) setStageError(message(e)); });
    return () => controller.abort();
  }, [guest?.csrf, mode, selected, retry]); // Progress updates don't erase success feedback.

  useEffect(() => {
    if (panel !== 'leaderboard' && panel !== 'treasure') return;
    setPanelError(''); setPanelLoading(true);
    const controller = new AbortController();
    const request = panel === 'leaderboard'
      ? api<{ items: Entry[]; total: number }>(`leaderboard?mode=${mode}&offset=${boardOffset}`, undefined, undefined, controller.signal)
        .then(data => { setEntries(data.items); setBoardTotal(data.total); })
      : api<Reward>(`treasure?mode=${mode}`, undefined, undefined, controller.signal).then(setReward);
    request.catch(e => { if (!controller.signal.aborted) setPanelError(message(e)); }).finally(() => { if (!controller.signal.aborted) setPanelLoading(false); });
    return () => controller.abort();
  }, [panel, mode, boardOffset, retry]);

  async function enter(event?: FormEvent, replay = false) {
    event?.preventDefault(); setBusy(true); setError('');
    try {
      const data = await api<Session>('session', { name: replay ? guest?.name : name.trim() });
      setGuest(data); setSelected(1); setReward(null); setPanel(null); setFeedback('');
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  function choose(id: number) {
    if (busy || id > current) return;
    setSelected(id);
    if (window.innerWidth < 1000) missionRef.current?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
  }
  function changeMode(value: Mode) {
    if (busy) return;
    setMode(value); setSelected(Math.min(5, (guest?.modes[value].solved.length || 0) + 1)); setReward(null); setBoardOffset(0); setError('');
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!guest) return;
    setBusy(true); setError(''); setFeedback('');
    try {
      const data = await api<{ correct: boolean; detail?: string; debrief?: string; session?: Session }>(`stages/${selected}/answers?mode=${mode}`, { flag }, guest.csrf);
      if (data.correct && data.session) { setGuest(data.session); setFeedback(data.debrief!); }
      else setError(data.detail || 'Kiểm tra lại flag nhé.');
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  async function hint() {
    if (!guest || !clue) return;
    setBusy(true); setError('');
    try {
      const data = await api<{ hints: string[] }>(`stages/${selected}/hints?mode=${mode}`, {}, guest.csrf);
      setClue({ ...clue, hints: data.hints });
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  async function copy(text: string) {
    try { await navigator.clipboard.writeText(text); setCopied('Đã sao chép.'); }
    catch { setCopied('Hãy chọn phần văn bản và sao chép thủ công.'); }
  }
  function openBoard() { setBoardOffset(0); setPanel('leaderboard'); }

  return <>
    <a className="skip-link" href="#mission">Đến nhiệm vụ</a>
    <header className="site-header">
      <a className="brand" href="/" aria-label="Đảo Mật Mã · CMC Infrasec · Trang chính"><ClubLogo /><span>ĐẢO MẬT MÃ<span className="brand-sub">NEXTFEST 26 / TREASURE HUNT</span></span></a>
      <nav aria-label="Điều hướng chính"><button aria-label="Cách chơi" onClick={() => setPanel('guide')}><BookOpenIcon /> <span>Cách chơi</span></button><button aria-label="Bảng xếp hạng" onClick={openBoard}><TrophyIcon /> <span>Bảng xếp hạng</span></button><button aria-label="Nhật ký" onClick={() => setPanel('journal')}><MapTrifoldIcon /> <span>Nhật ký</span></button></nav>
      <button className="icon-button theme-switch" aria-label={dark ? 'Bật giao diện sáng' : 'Bật giao diện tối'} onClick={() => {
        const value = !dark; setDark(value); document.documentElement.dataset.theme = value ? 'dark' : 'light'; localStorage.setItem('island-theme', value ? 'dark' : 'light');
      }}>{dark ? <SunIcon size={21} /> : <MoonIcon size={21} />}</button>
    </header>

    <main>
      <section className="intro" aria-labelledby="title">
        <div><p className="eyebrow"><span className="live-dot" /> NEXTFEST 26 · CHUYẾN ĐI CỦA NHỮNG NGƯỜI TÒ MÒ</p>
          <h1 id="title">Một hòn đảo.<br />Năm điều <span>bí mật.</span></h1>
          <p className="intro-copy">Không cần là hacker để bắt đầu. Lần theo manh mối, giải những mật mã đầu tiên — và tìm kho báu của riêng bạn.</p>
        </div>
        <aside className="expedition-note"><CompassIcon size={38} weight="duotone" /><span className="eyebrow">CHUYẾN THÁM HIỂM ĐẦU TIÊN</span><p>Bắt đầu bằng tò mò.<br />Trở về với một kỹ năng mới.</p><span className="note-bottom">5 địa điểm <span>·</span> 1 kho báu <span>·</span> Bạn</span></aside>
      </section>

      <section className="game-shell" aria-label="Chuyến săn kho báu">
        <div className="game-toolbar"><div className="mode-switch" role="group" aria-label="Độ khó"><button aria-pressed={mode === 'easy'} disabled={busy} onClick={() => changeMode('easy')}>Easy <span>Khởi đầu</span></button><button aria-pressed={mode === 'hard'} disabled={busy} onClick={() => changeMode('hard')}>Hard <span>Thử sức</span></button></div>
          <div className="player-chip">{guest ? <><span className="avatar">{guest.name.slice(0, 1).toUpperCase()}</span><span>{guest.name}</span><span className="score">{progress?.points || 0} điểm</span></> : <span><FlagIcon /> Dành cho người mới · Weight ≤ 10</span>}</div>
        </div>

        <div className={`game-columns ${guest ? '' : 'awaiting-captain'}`}><section className="map-panel" aria-labelledby="map-title">
          <div className="map-top"><div><p className="eyebrow">HẢI ĐỒ / 01</p><h2 id="map-title">Quần đảo mật mã</h2></div><span className="map-coordinate">21° N — 105° E<br />HƯỚNG ĐẾN ĐIỀU CHƯA BIẾT</span></div>
          <div className="island-map">
            <svg viewBox="0 0 800 420" preserveAspectRatio="none" className="map-art" aria-hidden="true">
              <defs><pattern id="ocean" width="32" height="32" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="currentColor" opacity=".12" /></pattern></defs>
              <rect width="800" height="420" fill="url(#ocean)" />
              <path d="M120 277 C130 130 230 190 272 139 S380 140 424 260 S525 250 576 122 S670 150 696 252" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="5 9" opacity=".33" />
              <g className="land"><path d="M45 287 L60 250 93 239 110 221 146 239 174 281 153 318 94 325 58 309Z" /><path d="M202 150 L224 102 261 88 304 99 328 139 310 176 267 188 220 174Z" /><path d="M357 270 L369 228 410 211 450 228 485 261 463 304 420 317 372 300Z" /><path d="M514 136 L529 84 560 62 600 76 638 120 615 159 566 174 526 158Z" /><path d="M641 264 L654 219 687 205 726 218 760 257 741 293 695 310 655 292Z" /></g>
              <g className="coast" fill="none"><path d="M39 290 Q41 219 106 212 M197 148 Q200 87 269 78 M350 272 Q350 210 413 201 M508 134 Q506 71 558 51 M636 267 Q638 207 692 194" /></g>
              <g className="sea-marks"><path d="M72 96q12-10 24 0t24 0 M344 61q12-10 24 0t24 0 M519 352q12-10 24 0t24 0 M225 348q12-10 24 0t24 0 M699 70q12-10 24 0t24 0" fill="none" stroke="currentColor" strokeWidth="2" /></g>
            </svg>
            {stages.map((stage, i) => {
              const Icon = icons[i]; const done = solved.includes(stage.id); const locked = stage.id > current;
              return <button key={stage.id} className={`map-node ${done ? 'done' : ''} ${selected === stage.id ? 'active' : ''} ${locked ? 'locked' : ''}`} style={positions[i]} onClick={() => choose(stage.id)} disabled={locked || busy} aria-current={selected === stage.id ? 'step' : undefined} aria-label={`${stage.id}. ${stage.location}${locked ? ' · Chưa mở' : done ? ' · Đã giải' : ' · Khám phá'}`}>
                <span className="node-number">{done ? <CheckIcon weight="bold" /> : locked ? <LockKeyIcon weight="bold" /> : `0${stage.id}`}</span>
                <Icon className="destination-icon" size={42} weight="duotone" /><span className="node-name">{stage.location}</span><span className="node-weight">{stage.category} · {stage.weight}/10</span>
              </button>;
            })}
            <span className="map-compass" aria-hidden="true"><span>N</span><CompassIcon size={36} weight="thin" /></span>
            <span className="map-caption">Mỗi bí mật mở ra một lối đi mới.</span>
          </div>

          <ol className="mobile-route" aria-label="Các địa điểm">{stages.map((s, i) => {
            const Icon = icons[i]; return <li key={s.id}><button className={selected === s.id ? 'selected' : ''} disabled={s.id > current || busy} onClick={() => choose(s.id)} aria-current={selected === s.id ? 'step' : undefined}><Icon size={24} /><span><small>0{s.id} / {s.weight}/10</small>{s.location}</span>{solved.includes(s.id) ? <CheckIcon /> : s.id > current ? <LockKeyIcon /> : <ArrowRightIcon />}</button></li>;
          })}</ol>

          <div className="fragment-bar"><div><span className="eyebrow">LA BÀN CỦA BẠN</span><p>{solved.length === 5 ? 'Đủ mảnh rồi. Kho báu đang chờ!' : `${solved.length}/5 mảnh đã tìm thấy`}</p></div><div className="fragments" aria-label={`${solved.length} trên 5 mảnh la bàn`}>{stages.map(s => <span key={s.id} className={solved.includes(s.id) ? 'earned' : ''}>{solved.includes(s.id) ? <CheckIcon weight="bold" /> : s.id}</span>)}</div></div>
          <button className={`treasure-strip ${solved.length === 5 ? 'unlocked' : ''}`} disabled={solved.length !== 5} onClick={() => setPanel('treasure')}><TreasureChestIcon size={29} weight="duotone" /><span><strong>Đích đến: kho báu NextFest 26</strong><small>Sticker logo CMC Infrasec · Thu thập đủ 5 mảnh để mở</small></span>{solved.length === 5 ? <ArrowRightIcon size={23} /> : <LockKeyIcon size={22} />}</button>
        </section>

        <section className="mission-panel" id="mission" ref={missionRef} aria-label="Nhiệm vụ hiện tại" tabIndex={-1}>
          {loading ? <div className="empty-state" role="status"><CircleNotchIcon className="spin" size={32} /><h2>Đang trải hải đồ…</h2><p>Chuẩn bị cho chuyến đi của bạn.</p></div> : !guest ? <div className="onboarding">
            <span className="eyebrow">THUYỀN ĐÃ SẴN SÀNG</span><span className="welcome-icon"><FlagIcon size={34} weight="duotone" /></span><h2>Thuyền trưởng,<br />bạn tên gì?</h2><p>Chọn một tên hiển thị. Không tài khoản, không mật khẩu. Chỉ cần một chút tò mò.</p>
            <form onSubmit={enter}><label htmlFor="guest-name">Tên trên bảng xếp hạng</label><input id="guest-name" name="name" autoComplete="nickname" minLength={2} maxLength={24} required value={name} onChange={e => setName(e.target.value)} placeholder="Ví dụ: Thuyền trưởng Mèo" /><button className="button full" disabled={busy || name.trim().length < 2} type="submit">{busy ? 'Đang lên thuyền…' : 'Bắt đầu thám hiểm'}<ArrowRightIcon size={20} /></button></form>
            <p className="small privacy-note">Tên và điểm sẽ xuất hiện công khai trên BXH. Tiến độ lưu theo trình duyệt trong 30 ngày.</p>
            <button className="text-button" onClick={() => setPanel('guide')}>Lần đầu nghe về CTF? <ArrowRightIcon /></button>
          </div> : stageError ? <div className="empty-state"><h2>Manh mối chưa đến nơi</h2><p role="alert">{stageError}</p><button className="button" onClick={() => setRetry(r => r + 1)}>Thử lại</button></div> : !clue || clue.id !== selected || clue.mode !== mode ? <div className="empty-state" role="status"><CircleNotchIcon className="spin" size={30} /><p>Đang tìm manh mối…</p></div> : <>
            <div className="mission-top"><span className="eyebrow">NHIỆM VỤ / 0{selected}</span><span className="category">{clue.category} <span>{clue.weight}/10</span></span></div>
            <h2>{clue.title}</h2><p className="mission-story">{clue.summary}</p>
            <div className="objective"><FlagIcon size={20} /><p>{clue.objective}</p></div>
            <div className="clue-heading"><label htmlFor="clue-data">MANH MỐI CỦA BẠN</label><button className="icon-button" aria-label="Sao chép manh mối" onClick={() => copy(clue.payload)}><CopyIcon size={17} /></button></div>
            <textarea readOnly id="clue-data" className="clue-data" value={clue.payload} rows={selected === 3 || selected === 4 ? 6 : 3} spellCheck={false} />
            <a className="artifact-link" href={`/api/v1/stages/${selected}/artifact?mode=${mode}`} download={clue.artifact_name}><DownloadSimpleIcon /> Tải {clue.artifact_name}</a>
            {mode === 'easy' ? <Bench key={`${mode}-${selected}`} clue={clue} useResult={setFlag} /> : <p className="hard-note small">Hard: tự chọn công cụ và nhận diện lớp mã. Ảnh PNG có thể đọc metadata bằng ExifTool hoặc Pillow.</p>}
            {isSolved ? <div className="success" role="status"><span className="success-title"><CheckIcon size={22} weight="bold" /> Đã tìm thấy mảnh la bàn!</span><p>{feedback || clue.debrief}</p><button className="button full" onClick={() => selected === 5 ? setPanel('treasure') : choose(selected + 1)}>{selected === 5 ? 'Mở kho báu' : 'Đến địa điểm tiếp theo'}<ArrowRightIcon /></button></div> : <>
              <form onSubmit={submit} className="flag-form"><label htmlFor="flag">Bạn tìm được flag nào?</label><input id="flag" name="flag" value={flag} onChange={e => setFlag(e.target.value)} placeholder="DAO{...}" maxLength={160} required spellCheck={false} autoComplete="off" /><button className="button full" type="submit" disabled={busy || !flag.trim()}>{busy ? 'Đang kiểm tra…' : 'Kiểm tra flag'}<ArrowRightIcon /></button></form>
              <div className="hints"><button className="text-button" disabled={busy || clue.hints.length === 3} onClick={hint}><LightbulbIcon size={18} />{clue.hints.length === 3 ? 'Đã mở hết gợi ý' : 'Cần một chút gợi ý?'}<span>{clue.hints.length}/3</span></button><small>Mỗi gợi ý trừ 25 điểm. Sai flag không trừ điểm.</small>{clue.hints.length > 0 && <ol>{clue.hints.map(h => <li key={h}>{h}</li>)}</ol>}</div>
            </>}
          </>}
          {error && <div className="error" role="alert">{error}{!guest && <button className="text-button" onClick={() => setRetry(r => r + 1)}>Kết nối lại</button>}</div>}
          <p className="copy-status" role="status">{copied}</p>
        </section></div>
      </section>

      <section className="below-map"><span><SparkleIcon size={22} /><strong>Học bằng cách khám phá.</strong> Mỗi màn là một kỹ năng, không phải bài kiểm tra.</span><button className="text-button" onClick={() => setPanel('guide')}>Đọc sổ tay tân binh <ArrowRightIcon /></button></section>
    </main>
    <footer><p>Ai cũng có một<br /><span>lần đầu phá mã.</span></p><div className="footer-bottom"><span className="footer-organizer"><ClubLogo placement="footer" /><span className="muted">× NextFest 26</span></span><span>5 bí mật. 1 chuyến đi đáng nhớ.</span>{guest && <button className="text-button" onClick={() => setPanel('replay')}><ArrowCounterClockwiseIcon /> Chuyến đi mới</button>}</div></footer>

    {panel && <Modal title={{ guide: 'Sổ tay tân binh', journal: 'Nhật ký thám hiểm', leaderboard: 'Bảng xếp hạng', replay: 'Bắt đầu chuyến đi mới?', treasure: 'Kho báu của bạn!' }[panel]} onClose={() => setPanel(null)}>
      {panel === 'guide' && <div className="guide-content"><p className="lead">CTF là trò tìm “lá cờ” — một chuỗi ký tự bí mật ẩn trong dữ liệu.</p><ol className="guide-steps"><li><strong>Đọc manh mối.</strong> Mỗi địa điểm dạy một kỹ năng mới. Easy có công cụ và ví dụ HELLO để bạn thử trước.</li><li><strong>Tìm chuỗi <code>DAO{'{...}'}</code>.</strong> Sao chép đủ dấu ngoặc, giữ nguyên chữ hoa. Không cần cài phần mềm khi chơi Easy.</li><li><strong>Nộp flag và ghép la bàn.</strong> Đúng thì mở địa điểm mới. Sai thì thử lại; điểm không bị trừ.</li><li><strong>Đến kho báu.</strong> Giải đủ năm màn rồi đưa mã hoàn thành cho ban tổ chức để nhận sticker logo CMC Infrasec tại NextFest 26.</li></ol><div className="guide-note"><h3>Điểm & độ khó</h3><p>Weight 2 → 10 là độ khó tương đối. Điểm mỗi màn = weight × 100 − 25 × số gợi ý. Tối đa 3.000 điểm mỗi mode. BXH ưu tiên số màn → điểm → thời gian hoàn thành.</p><p>Easy và Hard lưu tiến độ riêng. Tên có thể trùng; cookie mới là định danh. Giữ cookie để tiếp tục chuyến đi.</p></div><button className="button full" onClick={() => setPanel(null)}>Đã hiểu, lên đường thôi! <ArrowRightIcon /></button></div>}
      {panel === 'journal' && <div><p className="muted">Những điều bạn đã khám phá · {mode === 'easy' ? 'Easy' : 'Hard'}</p>{!solved.length ? <div className="empty-state"><BookOpenIcon size={38} /><p>Trang đầu vẫn còn trống.<br />Giải manh mối đầu tiên để viết câu chuyện của bạn.</p></div> : <ol className="journal-list">{stages.filter(s => solved.includes(s.id)).map(s => <li key={s.id}><CheckIcon /><div><strong>{s.location}</strong><p>{s.category} · Đã thu thập mảnh 0{s.id}</p><button className="text-button" onClick={() => { choose(s.id); setPanel(null); }}>Đọc lại bài học <ArrowRightIcon /></button></div></li>)}</ol>}</div>}
      {panel === 'leaderboard' && <><div className="board-toolbar"><p>{mode === 'easy' ? 'Easy · Khởi đầu' : 'Hard · Thử sức'}</p><button className="text-button" onClick={() => changeMode(mode === 'easy' ? 'hard' : 'easy')}>Xem {mode === 'easy' ? 'Hard' : 'Easy'} <ArrowRightIcon /></button></div><p className="small">Số màn → điểm → thời gian hoàn thành. Tên guest có thể trùng.</p>{!panelLoading && !panelError && (entries.length ? <div className="table-scroll"><table><caption className="sr-only">Thứ hạng người chơi {mode}</caption><thead><tr><th>#</th><th>Thuyền trưởng</th><th>Mảnh</th><th>Điểm</th><th>Thời gian</th></tr></thead><tbody>{entries.map((e, i) => <tr key={i}><td>{boardOffset + i + 1}</td><td>{e.name}</td><td>{e.solved}/5</td><td>{e.points}</td><td>{e.seconds === null ? 'Đang chơi' : `${Math.floor(e.seconds / 60)}p ${e.seconds % 60}s`}</td></tr>)}</tbody></table></div> : <div className="empty-state"><TrophyIcon size={38} /><p>Chưa có thuyền trưởng nào trên bảng.<br />Giải màn đầu tiên để ghi tên bạn!</p></div>)}<div className="button-row"><button className="button secondary small-button" disabled={boardOffset === 0 || panelLoading} onClick={() => setBoardOffset(v => Math.max(0, v - 20))}>Trang trước</button><span className="small">{boardTotal} chuyến đi</span><button className="button secondary small-button" disabled={boardOffset + 20 >= boardTotal || panelLoading} onClick={() => setBoardOffset(v => v + 20)}>Trang sau</button></div></>}
      {panel === 'replay' && <><p>Tiến độ và điểm hiện tại vẫn giữ trên BXH, nhưng trình duyệt sẽ chuyển sang một chuyến đi mới với flag mới. Chuyến cũ sẽ không còn truy cập bằng cookie này.</p><p>Tên hiển thị: <strong>{guest?.name}</strong></p><div className="button-row"><button className="button secondary" onClick={() => setPanel(null)}>Ở lại chuyến này</button><button className="button" disabled={busy} onClick={() => enter(undefined, true)}>Tạo chuyến mới <ArrowRightIcon /></button></div>{error && <p className="error" role="alert">{error}</p>}</>}
      {panel === 'treasure' && reward && !panelLoading && !panelError && <div className="reward"><span className="reward-illustration">{reward.logo_ready ? <ClubLogo placement="reward" /> : <TreasureChestIcon size={85} weight="duotone" />}</span><p className="eyebrow">NEXTFEST 26 / KHO BÁU CỦA BẠN</p><h3>Bạn đã phá đủ 5 mật mã.</h3><p><strong>{reward.name}</strong>, một sticker logo CMC Infrasec đang chờ bạn tại NextFest 26.</p><div className="reward-code"><span className="eyebrow">MÃ HOÀN THÀNH</span><strong data-testid="reward-code">{reward.code}</strong><button className="text-button" onClick={() => copy(reward.code)}><CopyIcon /> Sao chép mã</button></div><p>{reward.instruction}</p><p className="small">{mode === 'easy' ? 'Easy' : 'Hard'} · {progress?.points} điểm · {Math.floor(reward.seconds / 60)}p {reward.seconds % 60}s</p><p className="copy-status" role="status">{copied}</p><button className="button full" onClick={openBoard}>Ghi dấu trên bảng xếp hạng <TrophyIcon /></button></div>}
      {panelLoading && <p className="loading-line" role="status"><CircleNotchIcon className="spin" /> Đang mở hải đồ…</p>}
      {panelError && <div className="error" role="alert">{panelError}<button className="text-button" onClick={() => setRetry(r => r + 1)}>Thử lại</button></div>}
    </Modal>}
  </>;
}

