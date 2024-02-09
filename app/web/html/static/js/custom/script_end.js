tippy(".tippy", { allowHTML: true, animation: "scale-subtle" })

// Add Alpine.js magic to copy text to clipboard
// Call like this:
// @click="$clipboard('<thing to copy>'); pushNotify('Copied!')"
document.addEventListener("alpine:init", () => {
  Alpine.magic("clipboard", () => {
    return (subject) => navigator.clipboard.writeText(subject)
  })
})
