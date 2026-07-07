# Bug: label validator accepts mixed-script look-alike names

`is_allowed_label(label)` decides whether a user-chosen label (for a username
or a host label) is allowed. To stop homograph/look-alike spoofing, a label
must not combine letters from more than one script. It should also treat
labels that only differ by compatibility form as their normalized form.

Reported problems:

- `"gοοgle"` (Latin letters with two Greek omicrons) is accepted, even though
  it mixes Latin and Greek to imitate an all-Latin name.
- `"clasѕ"` (Latin with a trailing Cyrillic `ѕ`) is accepted.
- A genuine, single-script Cyrillic label such as `"привет"` is rejected even
  though every letter is Cyrillic.

Legitimate, single-script labels must be accepted:

- `"paypal"`, `"hello-world"`, `"user_2024"`.
- A Japanese label such as `"日本語ユーザー"` (Han + Katakana, treated as one
  script) is accepted.
- A fullwidth variant such as `"ｐａｙｐａｌ"` normalizes to `"paypal"` and is accepted.
