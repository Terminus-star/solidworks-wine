# Selawik font fallback

These five unmodified TrueType fonts are Microsoft's Selawik 1.01 release:
https://github.com/microsoft/Selawik/releases/tag/1.01

Upstream archive SHA-256:
`3f62c51e05e3b5a1e6241cf92a371f0be2ea1183aa87b30718bbd40832a8d423`

`LICENSE.txt` is the upstream SIL Open Font License 1.1 and copyright notice.
Selawik is a substitute, not the proprietary Segoe UI font. Its kerning and
hinting differ. The font files and their internal family names are unmodified.
Only this project's Wine prefix aliases the missing Segoe UI family to Selawik.
Wine gives a genuinely installed Segoe UI family precedence over this alias.
