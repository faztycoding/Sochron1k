# SOCHRON1K — Skills.sh ที่แนะนำ

> **skills.sh** คือ registry ของ AI Agent Skills — เป็น best practices แบบ modular
> ที่ติดตั้งให้ AI assistant (Claude Code, Cursor, Windsurf) เข้าใจโปรเจคดีขึ้น
>
> ติดตั้ง: `npx skills add <skill-name>`

---

## ระดับความสำคัญ

- 🔴 **CRITICAL** — ต้องใช้ ส่งผลต่อคุณภาพโค้ดโดยตรง
- 🟡 **HIGH** — แนะนำอย่างยิ่ง
- 🟢 **NICE-TO-HAVE** — มีดีกว่าไม่มี

---

## 1. Backend — Python & FastAPI

| # | Skill | Source | Level | คำสั่ง | ทำไมถึงต้องใช้ |
|---|---|---|---|---|---|
| 1 | **fastapi-python** | mindrally/skills | 🔴 | `npx skills add mindrally/skills/fastapi-python` | Best practices สำหรับ FastAPI: async patterns, Pydantic v2, dependency injection, error handling — **หัวใจหลักของ backend เรา** |
| 2 | **python-performance-optimization** | wshobson/agents | 🟡 | `npx skills add wshobson/agents/python-performance-optimization` | Optimize Python performance — สำคัญมากเพราะต้องรัน indicators + scraping + AI pipeline พร้อมกัน |
| 3 | **api-design-principles** | wshobson/agents | 🟡 | `npx skills add wshobson/agents/api-design-principles` | RESTful API design ที่ถูกต้อง — เรามี 20+ endpoints ต้องออกแบบให้ดี |

---

## 2. Frontend — Next.js, React, TypeScript

| # | Skill | Source | Level | คำสั่ง | ทำไมถึงต้องใช้ |
|---|---|---|---|---|---|
| 4 | **vercel-react-best-practices** | vercel-labs/agent-skills | 🔴 | `npx skills add vercel-labs/agent-skills/vercel-react-best-practices` | React best practices จาก Vercel เอง — ใช้กับ Dashboard, Charts, Signal Panel ทั้งหมด |
| 5 | **next-best-practices** | vercel-labs/next-skills | 🔴 | `npx skills add vercel-labs/next-skills/next-best-practices` | Next.js 15 App Router, Server Components, caching — ใช้ได้ทั้งโปรเจค |
| 6 | **next-cache-components** | vercel-labs/next-skills | 🟡 | `npx skills add vercel-labs/next-skills/next-cache-components` | Next.js caching strategy — สำคัญสำหรับ page ข่าวและ analysis ที่อัพเดทบ่อย |
| 7 | **vercel-composition-patterns** | vercel-labs/agent-skills | 🟢 | `npx skills add vercel-labs/agent-skills/vercel-composition-patterns` | Component composition — จัด structure components ใน Dashboard + Charts |
| 8 | **typescript-advanced-types** | wshobson/agents | 🟡 | `npx skills add wshobson/agents/typescript-advanced-types` | TypeScript types ที่ซับซ้อน — ใช้กับ API response types, WebSocket message types |

---

## 3. UI/UX & Design

| # | Skill | Source | Level | คำสั่ง | ทำไมถึงต้องใช้ |
|---|---|---|---|---|---|
| 9 | **shadcn** | shadcn/ui | 🔴 | `npx skills add shadcn/ui/shadcn` | shadcn/ui official skill — ใช้สร้าง UI components ทั้งหมด (tables, cards, forms, charts) |
| 10 | **tailwind-design-system** | wshobson/agents | 🟡 | `npx skills add wshobson/agents/tailwind-design-system` | Tailwind design system — consistent styling ทั้งแอพ |
| 11 | **tailwind-v4-shadcn** | jezweb/claude-skills | 🟡 | `npx skills add jezweb/claude-skills/tailwind-v4-shadcn` | Tailwind v4 + shadcn integration patterns — CSS variables, @theme |
| 12 | **frontend-design** | anthropics/skills | 🟡 | `npx skills add anthropics/skills/frontend-design` | Frontend design principles — layout, spacing, color, accessibility |
| 13 | **ui-ux-pro-max** | nextlevelbuilder/ui-ux-pro-max-skill | 🟢 | `npx skills add nextlevelbuilder/ui-ux-pro-max-skill/ui-ux-pro-max` | Pro-level UI/UX — ทำให้ Dashboard สวยและใช้งานง่าย |
| 14 | **web-design-guidelines** | vercel-labs/agent-skills | 🟢 | `npx skills add vercel-labs/agent-skills/web-design-guidelines` | Web design guidelines จาก Vercel |

---

## 4. Web Scraping & Browser Automation

| # | Skill | Source | Level | คำสั่ง | ทำไมถึงต้องใช้ |
|---|---|---|---|---|---|
| 15 | **playwright-best-practices** | currents-dev/playwright-best-practices-skill | 🔴 | `npx skills add currents-dev/playwright-best-practices-skill/playwright-best-practices` | Playwright patterns — ใช้ scrape Forex Factory (JS-rendered) ซึ่งเป็นแหล่งข้อมูลหลัก |
| 16 | **playwright-cli** | microsoft/playwright-cli | 🟡 | `npx skills add microsoft/playwright-cli/playwright-cli` | Playwright CLI จาก Microsoft — debugging, codegen |
| 17 | **browser-use** | browser-use/browser-use | 🟡 | `npx skills add browser-use/browser-use/browser-use` | Browser automation patterns — backup สำหรับ scraping ที่ซับซ้อน |
| 18 | **firecrawl** | firecrawl/cli | 🟢 | `npx skills add firecrawl/cli/firecrawl` | Firecrawl web scraping — alternative approach ถ้า Playwright ไม่ work กับบางเว็บ |
| 19 | **firecrawl-scrape** | firecrawl/cli | 🟢 | `npx skills add firecrawl/cli/firecrawl-scrape` | Firecrawl scraping-specific patterns |

---

## 5. Testing & Quality

| # | Skill | Source | Level | คำสั่ง | ทำไมถึงต้องใช้ |
|---|---|---|---|---|---|
| 20 | **test-driven-development** | obra/superpowers | 🔴 | `npx skills add obra/superpowers/test-driven-development` | TDD workflow — **สำคัญมาก** เพราะ signal logic ต้องถูกต้อง 100%, ทดสอบทุก indicator |
| 21 | **webapp-testing** | anthropics/skills | 🟡 | `npx skills add anthropics/skills/webapp-testing` | Web app testing patterns — test API endpoints, WebSocket, frontend |
| 22 | **systematic-debugging** | obra/superpowers | 🟡 | `npx skills add obra/superpowers/systematic-debugging` | Debugging methodology — ใช้หา bug ใน analysis pipeline ที่ซับซ้อน |
| 23 | **verification-before-completion** | obra/superpowers | 🟡 | `npx skills add obra/superpowers/verification-before-completion` | ตรวจสอบก่อน commit — ลด bug ก่อน deploy |

---

## 6. Development Workflow & Planning

| # | Skill | Source | Level | คำสั่ง | ทำไมถึงต้องใช้ |
|---|---|---|---|---|---|
| 24 | **executing-plans** | obra/superpowers | 🔴 | `npx skills add obra/superpowers/executing-plans` | Execute implementation plans อย่างเป็นระบบ — โปรเจคนี้มี 9 phases ต้อง manage ดี |
| 25 | **writing-plans** | obra/superpowers | 🟡 | `npx skills add obra/superpowers/writing-plans` | เขียนแผนที่ดี — update plan เมื่อพบปัญหา |
| 26 | **git-commit** | github/awesome-copilot | 🟡 | `npx skills add github/awesome-copilot/git-commit` | Git commit best practices — conventional commits, meaningful messages |
| 27 | **github-actions-docs** | xixu-me/skills | 🟢 | `npx skills add xixu-me/skills/github-actions-docs` | CI/CD setup — auto-test เมื่อ push code |

---

## 7. Security & DevOps

| # | Skill | Source | Level | คำสั่ง | ทำไมถึงต้องใช้ |
|---|---|---|---|---|---|
| 28 | **harden** | pbakaus/impeccable | 🟡 | `npx skills add pbakaus/impeccable/harden` | Security hardening — ป้องกัน API keys leak, SQL injection, rate limiting |

---

## 8. AI Integration

| # | Skill | Source | Level | คำสั่ง | ทำไมถึงต้องใช้ |
|---|---|---|---|---|---|
| 29 | **ai-sdk** | vercel/ai | 🟢 | `npx skills add vercel/ai/ai-sdk` | Vercel AI SDK patterns — อาจใช้ได้กับ Gemini/Claude client integration |

---

## Quick Install — ทั้งหมดที่สำคัญ (🔴 CRITICAL)

```bash
# === CRITICAL: ต้องติดตั้งก่อนเริ่มเขียนโค้ด ===
npx skills add mindrally/skills/fastapi-python
npx skills add vercel-labs/agent-skills/vercel-react-best-practices
npx skills add vercel-labs/next-skills/next-best-practices
npx skills add shadcn/ui/shadcn
npx skills add currents-dev/playwright-best-practices-skill/playwright-best-practices
npx skills add obra/superpowers/test-driven-development
npx skills add obra/superpowers/executing-plans
```

## Quick Install — ทั้งหมดที่แนะนำ (🟡 HIGH)

```bash
# === HIGH: ติดตั้งเพิ่มเติมเพื่อคุณภาพสูงสุด ===
npx skills add wshobson/agents/python-performance-optimization
npx skills add wshobson/agents/api-design-principles
npx skills add vercel-labs/next-skills/next-cache-components
npx skills add wshobson/agents/typescript-advanced-types
npx skills add wshobson/agents/tailwind-design-system
npx skills add jezweb/claude-skills/tailwind-v4-shadcn
npx skills add anthropics/skills/frontend-design
npx skills add microsoft/playwright-cli/playwright-cli
npx skills add browser-use/browser-use/browser-use
npx skills add anthropics/skills/webapp-testing
npx skills add obra/superpowers/systematic-debugging
npx skills add obra/superpowers/verification-before-completion
npx skills add obra/superpowers/writing-plans
npx skills add github/awesome-copilot/git-commit
npx skills add pbakaus/impeccable/harden
```

## Install ALL (ทุกตัว ทีเดียว)

```bash
# Run all at once
npx skills add \
  mindrally/skills/fastapi-python \
  vercel-labs/agent-skills/vercel-react-best-practices \
  vercel-labs/next-skills/next-best-practices \
  shadcn/ui/shadcn \
  currents-dev/playwright-best-practices-skill/playwright-best-practices \
  obra/superpowers/test-driven-development \
  obra/superpowers/executing-plans \
  wshobson/agents/python-performance-optimization \
  wshobson/agents/api-design-principles \
  vercel-labs/next-skills/next-cache-components \
  wshobson/agents/typescript-advanced-types \
  wshobson/agents/tailwind-design-system \
  jezweb/claude-skills/tailwind-v4-shadcn \
  anthropics/skills/frontend-design \
  ui-ux-pro-max \
  web-design-guidelines \
  microsoft/playwright-cli/playwright-cli \
  browser-use/browser-use/browser-use \
  firecrawl/cli/firecrawl \
  anthropics/skills/webapp-testing \
  obra/superpowers/systematic-debugging \
  obra/superpowers/verification-before-completion \
  obra/superpowers/writing-plans \
  github/awesome-copilot/git-commit \
  xixu-me/skills/github-actions-docs \
  pbakaus/impeccable/harden \
  vercel/ai/ai-sdk

echo "✅ All Sochron1k skills installed!"
```

---

## Skills ↔ Sochron1k Module Mapping

| Sochron1k Module | Skills ที่เกี่ยวข้อง |
|---|---|
| **Backend API (FastAPI)** | fastapi-python, api-design-principles, python-performance-optimization |
| **Web Scraping** | playwright-best-practices, playwright-cli, browser-use, firecrawl |
| **AI Pipeline** | ai-sdk |
| **Indicators Engine** | python-performance-optimization, test-driven-development |
| **Analysis Brain** | test-driven-development, systematic-debugging |
| **Frontend Dashboard** | vercel-react-best-practices, next-best-practices, shadcn, tailwind-design-system |
| **Real-time Charts** | next-cache-components, typescript-advanced-types |
| **Trade Calculator** | shadcn, frontend-design, ui-ux-pro-max |
| **Trade Journal** | webapp-testing, verification-before-completion |
| **Docker Deploy** | harden, github-actions-docs |
| **Project Management** | executing-plans, writing-plans, git-commit |
