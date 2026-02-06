import { useState, useEffect } from "react";

const WEATHER_OPTIONS = [
  { value: 5, icon: "☀️", label: "とても良い", bg: "#ecfdf5", border: "#6ee7b7", activeBg: "#059669", activeText: "#fff" },
  { value: 4, icon: "🌤️", label: "やや良い", bg: "#f0fdf4", border: "#86efac", activeBg: "#16a34a", activeText: "#fff" },
  { value: 3, icon: "⛅", label: "普通", bg: "#fefce8", border: "#fde047", activeBg: "#ca8a04", activeText: "#fff" },
  { value: 2, icon: "🌧️", label: "やや悪い", bg: "#fff7ed", border: "#fdba74", activeBg: "#ea580c", activeText: "#fff" },
  { value: 1, icon: "⛈️", label: "とても悪い", bg: "#fef2f2", border: "#fca5a5", activeBg: "#dc2626", activeText: "#fff" },
];

const QUESTIONS = [
  {
    key: "work",
    num: 1,
    title: "仕事満足度",
    description: "現在の仕事内容や業務量に対する満足度はいかがですか？",
    icon: "💼",
  },
  {
    key: "relationship",
    num: 2,
    title: "人間関係",
    description: "上司・同僚との関係性やチームの雰囲気はいかがですか？",
    icon: "🤝",
  },
  {
    key: "health",
    num: 3,
    title: "健康",
    description: "心身の健康状態はいかがですか？（体調・睡眠・ストレスなど）",
    icon: "💪",
  },
];

export default function SurveyPage() {
  const [step, setStep] = useState("intro"); // intro | survey | confirm | done
  const [answers, setAnswers] = useState({ work: null, relationship: null, health: null });
  const [comment, setComment] = useState("");
  const [currentQ, setCurrentQ] = useState(0);
  const [fadeIn, setFadeIn] = useState(true);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const answered = Object.values(answers).filter(v => v !== null).length;
    setProgress((answered / 3) * 100);
  }, [answers]);

  const transition = (callback) => {
    setFadeIn(false);
    setTimeout(() => { callback(); setFadeIn(true); }, 250);
  };

  const selectAnswer = (key, value) => {
    setAnswers({ ...answers, [key]: value });
    if (currentQ < 2) {
      setTimeout(() => transition(() => setCurrentQ(currentQ + 1)), 350);
    } else {
      setTimeout(() => transition(() => setStep("comment")), 350);
    }
  };

  const allAnswered = Object.values(answers).filter(v => v !== null).length === 3;

  return (
    <div style={styles.wrapper}>
      <style>{globalCSS}</style>

      {/* Background decoration */}
      <div style={styles.bgDecor1} />
      <div style={styles.bgDecor2} />

      <div style={styles.container}>
        {/* Header */}
        <header style={styles.header}>
          <div style={styles.logoRow}>
            <div style={styles.logo}>G</div>
            <div>
              <div style={styles.logoTitle}>パルスサーベイ</div>
              <div style={styles.logoSub}>2026年2月度</div>
            </div>
          </div>
          {step === "survey" && (
            <div style={styles.progressWrap}>
              <div style={styles.progressBar}>
                <div style={{ ...styles.progressFill, width: `${progress}%` }} />
              </div>
              <span style={styles.progressText}>{Object.values(answers).filter(v => v !== null).length}/3</span>
            </div>
          )}
        </header>

        {/* Content */}
        <main style={{ ...styles.main, opacity: fadeIn ? 1 : 0, transform: fadeIn ? "translateY(0)" : "translateY(8px)" }}>

          {/* ── Intro Screen ── */}
          {step === "intro" && (
            <div style={styles.introCard}>
              <div style={styles.introIconWrap}>
                <span style={{ fontSize: 48 }}>📋</span>
              </div>
              <h1 style={styles.introTitle}>今月のコンディションを教えてください</h1>
              <p style={styles.introDesc}>
                3つの質問にお天気マークで答えるだけ。<br />
                所要時間は約1分です。
              </p>
              <div style={styles.trustBadges}>
                <TrustItem icon="🔒" text="人事担当のみ閲覧" />
                <TrustItem icon="🚫" text="評価には影響しません" />
                <TrustItem icon="⏱️" text="約1分で完了" />
              </div>
              <button onClick={() => transition(() => setStep("survey"))} style={styles.startBtn}>
                回答をはじめる
                <span style={{ marginLeft: 8 }}>→</span>
              </button>
              <p style={styles.deadline}>回答期限：2026年2月14日（土）</p>
            </div>
          )}

          {/* ── Survey Questions ── */}
          {step === "survey" && (
            <div>
              {/* Question tabs */}
              <div style={styles.qTabs}>
                {QUESTIONS.map((q, i) => (
                  <button
                    key={q.key}
                    onClick={() => transition(() => setCurrentQ(i))}
                    style={{
                      ...styles.qTab,
                      ...(currentQ === i ? styles.qTabActive : {}),
                      ...(answers[q.key] !== null ? styles.qTabDone : {}),
                    }}
                  >
                    <span style={{ fontSize: 14 }}>{answers[q.key] !== null ? "✓" : q.num}</span>
                    <span style={styles.qTabLabel}>{q.title}</span>
                  </button>
                ))}
              </div>

              {/* Current Question */}
              <div style={styles.questionCard}>
                <div style={styles.qHeader}>
                  <span style={{ fontSize: 32 }}>{QUESTIONS[currentQ].icon}</span>
                  <div>
                    <div style={styles.qNum}>質問 {QUESTIONS[currentQ].num}</div>
                    <h2 style={styles.qTitle}>{QUESTIONS[currentQ].title}</h2>
                  </div>
                </div>
                <p style={styles.qDesc}>{QUESTIONS[currentQ].description}</p>

                <div style={styles.weatherGrid}>
                  {WEATHER_OPTIONS.map(w => {
                    const isSelected = answers[QUESTIONS[currentQ].key] === w.value;
                    return (
                      <button
                        key={w.value}
                        onClick={() => selectAnswer(QUESTIONS[currentQ].key, w.value)}
                        style={{
                          ...styles.weatherCard,
                          background: isSelected ? w.activeBg : w.bg,
                          borderColor: isSelected ? w.activeBg : w.border,
                          transform: isSelected ? "scale(1.05)" : "scale(1)",
                          boxShadow: isSelected ? `0 8px 24px ${w.activeBg}44` : "0 2px 8px rgba(0,0,0,0.04)",
                        }}
                      >
                        <span style={{ fontSize: 36, filter: isSelected ? "none" : "none" }}>{w.icon}</span>
                        <span style={{
                          fontSize: 12, fontWeight: 600, marginTop: 4,
                          color: isSelected ? w.activeText : "#475569",
                        }}>
                          {w.label}
                        </span>
                      </button>
                    );
                  })}
                </div>

                {/* Nav */}
                <div style={styles.qNav}>
                  {currentQ > 0 && (
                    <button onClick={() => transition(() => setCurrentQ(currentQ - 1))} style={styles.navBtnBack}>
                      ← 前の質問
                    </button>
                  )}
                  <div style={{ flex: 1 }} />
                  {currentQ < 2 ? (
                    <button
                      onClick={() => transition(() => setCurrentQ(currentQ + 1))}
                      disabled={answers[QUESTIONS[currentQ].key] === null}
                      style={{
                        ...styles.navBtnNext,
                        opacity: answers[QUESTIONS[currentQ].key] !== null ? 1 : 0.4,
                      }}
                    >
                      次の質問 →
                    </button>
                  ) : (
                    <button
                      onClick={() => transition(() => setStep("comment"))}
                      disabled={!allAnswered}
                      style={{
                        ...styles.navBtnNext,
                        opacity: allAnswered ? 1 : 0.4,
                      }}
                    >
                      コメントへ →
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── Comment Screen ── */}
          {step === "comment" && (
            <div style={styles.questionCard}>
              <div style={styles.qHeader}>
                <span style={{ fontSize: 32 }}>💬</span>
                <div>
                  <div style={styles.qNum}>任意</div>
                  <h2 style={styles.qTitle}>フリーコメント</h2>
                </div>
              </div>
              <p style={styles.qDesc}>
                仕事・チーム・健康などについて伝えたいことがあれば、自由にご記入ください。
              </p>
              <textarea
                value={comment}
                onChange={e => setComment(e.target.value)}
                placeholder="例: 最近チームの雰囲気が良くなっていると感じます..."
                style={styles.commentBox}
                rows={5}
              />

              {/* Summary */}
              <div style={styles.summaryWrap}>
                <div style={styles.summaryTitle}>回答内容の確認</div>
                <div style={styles.summaryGrid}>
                  {QUESTIONS.map(q => {
                    const w = WEATHER_OPTIONS.find(o => o.value === answers[q.key]);
                    return (
                      <div key={q.key} style={styles.summaryItem}>
                        <span style={{ fontSize: 12, color: "#64748b" }}>{q.title}</span>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                          <span style={{ fontSize: 22 }}>{w?.icon}</span>
                          <span style={{ fontSize: 13, fontWeight: 600, color: "#334155" }}>{w?.label}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div style={styles.qNav}>
                <button onClick={() => transition(() => { setStep("survey"); setCurrentQ(2); })} style={styles.navBtnBack}>
                  ← 質問に戻る
                </button>
                <div style={{ flex: 1 }} />
                <button onClick={() => transition(() => setStep("done"))} style={styles.submitBtn}>
                  回答を送信する ✓
                </button>
              </div>
            </div>
          )}

          {/* ── Done Screen ── */}
          {step === "done" && (
            <div style={styles.doneCard}>
              <div style={styles.doneIconWrap}>
                <span style={{ fontSize: 56 }}>🎉</span>
              </div>
              <h2 style={styles.doneTitle}>回答ありがとうございました！</h2>
              <p style={styles.doneDesc}>
                今月のサーベイは完了です。<br />
                いただいた回答は、職場環境の改善に役立てさせていただきます。
              </p>

              <div style={styles.doneSummary}>
                {QUESTIONS.map(q => {
                  const w = WEATHER_OPTIONS.find(o => o.value === answers[q.key]);
                  return (
                    <div key={q.key} style={styles.doneSummaryRow}>
                      <span style={{ fontSize: 13, color: "#64748b", width: 90 }}>{q.title}</span>
                      <span style={{ fontSize: 20 }}>{w?.icon}</span>
                      <span style={{ fontSize: 13, fontWeight: 600, color: "#334155" }}>{w?.label}</span>
                    </div>
                  );
                })}
                {comment && (
                  <div style={{ marginTop: 12, padding: "10px 14px", background: "#f8fafc", borderRadius: 8, fontSize: 13, color: "#475569" }}>
                    💬 {comment}
                  </div>
                )}
              </div>

              <p style={styles.doneFooter}>
                来月のサーベイは3月上旬にお届けします。<br />
                何かお困りのことがあれば、いつでも人事部までご相談ください。
              </p>

              <button
                onClick={() => {
                  transition(() => {
                    setStep("intro");
                    setAnswers({ work: null, relationship: null, health: null });
                    setComment("");
                    setCurrentQ(0);
                  });
                }}
                style={styles.resetBtn}
              >
                デモ: もう一度回答する
              </button>
            </div>
          )}
        </main>

        {/* Footer */}
        <footer style={styles.footer}>
          <div style={{ fontSize: 11, color: "#94a3b8" }}>
            このサーベイは人事部が管理しています。回答内容は人事担当者のみが閲覧します。
          </div>
          <div style={{ fontSize: 11, color: "#cbd5e1", marginTop: 4 }}>
            © 2026 社内パルスサーベイシステム
          </div>
        </footer>
      </div>
    </div>
  );
}

function TrustItem({ icon, text }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#475569" }}>
      <span style={{ fontSize: 16 }}>{icon}</span>
      <span>{text}</span>
    </div>
  );
}

// ─── Styles ─────────────────────────────────────────────────
const globalCSS = `
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;600;700;800&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Noto Sans JP', -apple-system, BlinkMacSystemFont, sans-serif; background: #f0f4f8; }
  button { cursor: pointer; font-family: inherit; }
  textarea { font-family: inherit; }
  ::selection { background: #6366f133; }
`;

const styles = {
  wrapper: {
    minHeight: "100vh",
    background: "linear-gradient(160deg, #eef2ff 0%, #f0f4f8 40%, #faf5ff 100%)",
    position: "relative",
    overflow: "hidden",
  },
  bgDecor1: {
    position: "fixed", top: -120, right: -120, width: 400, height: 400,
    borderRadius: "50%", background: "radial-gradient(circle, #6366f108, transparent 70%)",
    pointerEvents: "none",
  },
  bgDecor2: {
    position: "fixed", bottom: -80, left: -80, width: 300, height: 300,
    borderRadius: "50%", background: "radial-gradient(circle, #a78bfa08, transparent 70%)",
    pointerEvents: "none",
  },
  container: {
    maxWidth: 520, margin: "0 auto", padding: "0 16px",
    minHeight: "100vh", display: "flex", flexDirection: "column",
  },
  header: {
    padding: "20px 0 12px", display: "flex", justifyContent: "space-between", alignItems: "center",
  },
  logoRow: { display: "flex", alignItems: "center", gap: 10 },
  logo: {
    width: 36, height: 36, borderRadius: 10,
    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    display: "flex", alignItems: "center", justifyContent: "center",
    color: "#fff", fontWeight: 800, fontSize: 18,
  },
  logoTitle: { fontSize: 15, fontWeight: 700, color: "#1e1b4b" },
  logoSub: { fontSize: 11, color: "#8b5cf6", fontWeight: 500 },
  progressWrap: { display: "flex", alignItems: "center", gap: 8 },
  progressBar: { width: 80, height: 6, background: "#e2e8f0", borderRadius: 3, overflow: "hidden" },
  progressFill: {
    height: "100%", background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
    borderRadius: 3, transition: "width 0.4s ease",
  },
  progressText: { fontSize: 12, color: "#6366f1", fontWeight: 600 },
  main: {
    flex: 1, display: "flex", flexDirection: "column", justifyContent: "center",
    padding: "8px 0 24px",
    transition: "opacity 0.25s ease, transform 0.25s ease",
  },

  // Intro
  introCard: {
    background: "#fff", borderRadius: 20, padding: "36px 28px", textAlign: "center",
    boxShadow: "0 4px 24px rgba(99,102,241,0.08), 0 1px 4px rgba(0,0,0,0.04)",
  },
  introIconWrap: {
    width: 80, height: 80, borderRadius: "50%", margin: "0 auto 20px",
    background: "linear-gradient(135deg, #eef2ff, #f5f3ff)",
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  introTitle: { fontSize: 20, fontWeight: 800, color: "#1e1b4b", lineHeight: 1.5, marginBottom: 10 },
  introDesc: { fontSize: 14, color: "#64748b", lineHeight: 1.7, marginBottom: 24 },
  trustBadges: {
    display: "flex", flexDirection: "column", gap: 10, alignItems: "center",
    padding: "16px 20px", background: "#f8fafc", borderRadius: 12, marginBottom: 24,
  },
  startBtn: {
    width: "100%", padding: "16px 24px", fontSize: 16, fontWeight: 700,
    background: "linear-gradient(135deg, #6366f1, #7c3aed)", color: "#fff",
    border: "none", borderRadius: 14,
    boxShadow: "0 4px 16px rgba(99,102,241,0.3)",
    transition: "all 0.2s",
  },
  deadline: { fontSize: 12, color: "#94a3b8", marginTop: 14 },

  // Question tabs
  qTabs: { display: "flex", gap: 8, marginBottom: 16 },
  qTab: {
    flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
    padding: "10px 8px", borderRadius: 10, border: "2px solid #e2e8f0",
    background: "#fff", fontSize: 13, color: "#94a3b8", fontWeight: 500,
    transition: "all 0.2s",
  },
  qTabActive: { borderColor: "#6366f1", color: "#6366f1", background: "#eef2ff" },
  qTabDone: { borderColor: "#10b981", color: "#059669", background: "#ecfdf5" },
  qTabLabel: { fontSize: 12 },

  // Question card
  questionCard: {
    background: "#fff", borderRadius: 20, padding: "28px 24px",
    boxShadow: "0 4px 24px rgba(99,102,241,0.08), 0 1px 4px rgba(0,0,0,0.04)",
  },
  qHeader: { display: "flex", alignItems: "center", gap: 14, marginBottom: 8 },
  qNum: { fontSize: 11, color: "#8b5cf6", fontWeight: 600, letterSpacing: 0.5 },
  qTitle: { fontSize: 18, fontWeight: 700, color: "#1e1b4b", margin: 0 },
  qDesc: { fontSize: 14, color: "#64748b", lineHeight: 1.6, marginBottom: 24, paddingLeft: 46 },

  // Weather grid
  weatherGrid: { display: "flex", justifyContent: "center", gap: 10, flexWrap: "wrap", marginBottom: 24 },
  weatherCard: {
    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
    width: 82, height: 88, borderRadius: 14, border: "2px solid",
    transition: "all 0.25s ease", padding: 8,
  },

  // Navigation
  qNav: { display: "flex", alignItems: "center", gap: 8, paddingTop: 8, borderTop: "1px solid #f1f5f9" },
  navBtnBack: {
    padding: "10px 18px", fontSize: 13, fontWeight: 500, color: "#64748b",
    background: "transparent", border: "1px solid #e2e8f0", borderRadius: 10,
    transition: "all 0.15s",
  },
  navBtnNext: {
    padding: "10px 20px", fontSize: 13, fontWeight: 600, color: "#fff",
    background: "#6366f1", border: "none", borderRadius: 10,
    transition: "all 0.15s",
  },
  submitBtn: {
    padding: "12px 24px", fontSize: 14, fontWeight: 700, color: "#fff",
    background: "linear-gradient(135deg, #6366f1, #7c3aed)", border: "none", borderRadius: 12,
    boxShadow: "0 4px 16px rgba(99,102,241,0.3)", transition: "all 0.2s",
  },

  // Comment
  commentBox: {
    width: "100%", padding: "14px 16px", border: "2px solid #e2e8f0", borderRadius: 12,
    fontSize: 14, color: "#334155", resize: "vertical", outline: "none",
    transition: "border-color 0.2s", lineHeight: 1.6,
    minHeight: 100,
  },
  summaryWrap: {
    marginTop: 20, padding: "16px 18px", background: "#f8fafc", borderRadius: 12,
    marginBottom: 20,
  },
  summaryTitle: { fontSize: 12, fontWeight: 600, color: "#6366f1", marginBottom: 12 },
  summaryGrid: { display: "flex", gap: 12 },
  summaryItem: { flex: 1, textAlign: "center" },

  // Done
  doneCard: {
    background: "#fff", borderRadius: 20, padding: "36px 28px", textAlign: "center",
    boxShadow: "0 4px 24px rgba(99,102,241,0.08), 0 1px 4px rgba(0,0,0,0.04)",
  },
  doneIconWrap: {
    width: 90, height: 90, borderRadius: "50%", margin: "0 auto 20px",
    background: "linear-gradient(135deg, #ecfdf5, #f0fdf4)",
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  doneTitle: { fontSize: 20, fontWeight: 800, color: "#1e1b4b", marginBottom: 10 },
  doneDesc: { fontSize: 14, color: "#64748b", lineHeight: 1.7, marginBottom: 20 },
  doneSummary: {
    padding: "18px 20px", background: "#f8fafc", borderRadius: 12, marginBottom: 20,
    display: "flex", flexDirection: "column", gap: 10,
  },
  doneSummaryRow: { display: "flex", alignItems: "center", gap: 10 },
  doneFooter: { fontSize: 13, color: "#94a3b8", lineHeight: 1.7, marginBottom: 16 },
  resetBtn: {
    padding: "10px 20px", fontSize: 13, fontWeight: 500, color: "#6366f1",
    background: "#eef2ff", border: "none", borderRadius: 10,
  },

  // Footer
  footer: { padding: "16px 0 20px", textAlign: "center" },
};
