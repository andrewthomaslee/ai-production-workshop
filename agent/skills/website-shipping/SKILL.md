---
name: website-shipping
description: Turn a brief into a deployed website: write the files, then ship to a live URL.
---

# Website shipping skill

You take a brief and produce a **deployed, live** website. The whole loop:

1. **Clarify the brief** briefly if needed: purpose, audience, vibe, key content
   and call-to-action. Don't over-ask; sensible defaults are fine.
2. **Build the files** in a workspace subdirectory (e.g. `site/`):
   - Write `site/index.html` with `write_file`. Make it a single, self-contained
     page: inline `<style>` (no external build step), semantic HTML, a hero
     section, the key content, and a clear CTA. Modern, clean, responsive.
   - Add assets only if needed; keep it to one file when you can.
3. **Deploy** with `deploy_site`, passing the directory (`site`) and a URL
   `slug` (e.g. the brand name, kebab-case). This returns a real live URL.
4. **Hand off**: give the user the URL and a one-line summary of what you built.

## Quality bar
- It must look intentional: spacing, a coherent color palette, readable type.
- Mobile-friendly (a simple responsive layout / flexbox).
- No Lorem Ipsum unless the user truly gave you nothing; infer reasonable copy
  from the brief.

## Permissions note
`deploy_site` is an **admin-only** action. If you are running as a lower role you
can still build the files, but deployment will be denied; tell the user they
need an admin to ship it. This is the role model working as intended.
