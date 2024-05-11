tippy(".tippy", { allowHTML: true, animation: "scale-subtle" })
setAllMediaWidthHeight()

// Add freezeframe.js to GIFs
// https://github.com/ctrl-freaks/freezeframe.js/tree/master/packages/freezeframe
const allGifs = document.querySelectorAll('img[src$=".gif"]')
;[...allGifs].forEach((gif) => {
  new Freezeframe({
    selector: gif,
    trigger: "click",
    overlay: true,
    responsive: false,
  })
})
