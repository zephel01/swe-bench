{
  "vulnerability": "path traversal",
  "mechanism": "The application joins attacker-controlled input onto a base directory without normalising the result, so a relative segment such as .. walks up out of the intended directory and the request reaches files elsewhere on the filesystem.",
  "mitigation": "Resolve the joined path to its canonical absolute form (for example with realpath) and reject it unless it is still inside the intended base directory; prefer an allow-list of known filenames over free-form user-supplied paths."
}
