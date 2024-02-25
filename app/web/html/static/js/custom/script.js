function pushNotify(title, text = "", status = "success", autotimeout = 3000) {
  new Notify({
    status: status,
    title: title,
    text: text,
    effect: "slide", // slide, fade
    speed: 500,
    customClass: "",
    customIcon: "",
    showIcon: true,
    showCloseButton: true,
    autoclose: true,
    autotimeout: autotimeout,
    gap: 20,
    distance: 20,
    type: 1,
    position: "right bottom",
  })
}

function copyTextToClipboard(text, message = "Copied!") {
  navigator.clipboard
    .writeText(text.trim())
    .then(() => {
      pushNotify(message)
    })
    .catch((err) => {
      pushNotify("Error", "Failed to copy to clipboard", null, "error")
    })
}

function copyElementToClipboard(selector, message = "Copied!") {
  const element = document.querySelector(selector)
  let textToCopy = element.innerHTML
  textToCopy = textToCopy.replace(/>(\s*)(.*?)(\s*)</g, ">$2<").trim()
  copyTextToClipboard(textToCopy, message)
}

function setElementWidthHeight(element) {
  if (element.tagName === "IMG") {
    const image = new Image()
    image.onload = function () {
      element.setAttribute("width", this.naturalWidth)
      element.setAttribute("height", this.naturalHeight)
    }
    image.src = element.src
  } else if (element.tagName === "VIDEO") {
    element.addEventListener("loadedmetadata", function () {
      element.setAttribute("width", this.videoWidth)
      element.setAttribute("height", this.videoHeight)
    })
  }
}

function setAllMediaWidthHeight() {
  // Select all img and video elements
  const mediaElements = document.querySelectorAll(
    "img:not([width]):not([height]), video:not([width]):not([height])"
  )
  mediaElements.forEach((element) => {
    setElementWidthHeight(element)
  })
}

// Lazy load videos
document.addEventListener("DOMContentLoaded", function () {
  const lazyVideos = [].slice.call(document.querySelectorAll("video.lazy"))

  if ("IntersectionObserver" in window) {
    const lazyVideoObserver = new IntersectionObserver(function (
      entries,
      observer
    ) {
      entries.forEach(function (video) {
        if (video.isIntersecting) {
          for (const source in video.target.children) {
            const videoSource = video.target.children[source]
            if (
              typeof videoSource.tagName === "string" &&
              videoSource.tagName === "SOURCE"
            ) {
              videoSource.src = videoSource.dataset.src
            }
          }

          video.target.load()
          video.target.classList.remove("lazy")
          lazyVideoObserver.unobserve(video.target)
        }
      })
    })

    lazyVideos.forEach(function (lazyVideo) {
      lazyVideoObserver.observe(lazyVideo)
    })
  }
})
