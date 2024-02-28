// Push a notification message to the screen
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

// Copy text to the clipboard
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

// Copy the innerHTML of an element to the clipboard
function copyElementToClipboard(selector, message = "Copied!") {
  const element = document.querySelector(selector)
  let textToCopy = element.innerHTML
  textToCopy = textToCopy.replace(/>(\s*)(.*?)(\s*)</g, ">$2<").trim()
  copyTextToClipboard(textToCopy, message)
}

// Set width and height attributes for an individual img or video element
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

// Set width and height attributes for all img and video elements
// If they are missing
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

// Highlight the table of contents element that corresponds to the current
// scroll position (in blog posts)
function highlightTocElement(id) {
  const navLinks = document.querySelectorAll("#toc a")
  const highlightedNavLink = document.querySelector(`#toc a[href='#${id}']`)
  if (!highlightedNavLink) {
    return
  }
  navLinks.forEach((a) => {
    a.classList.remove("blog-nav-highlight")
  })
  highlightedNavLink.classList.add("blog-nav-highlight")
}

// Add a confirm dialog popup to all elements with the `confirm` class
function addConfirmEventListener(id) {
  const el = document.getElementById(id)
  if (!el) {
    return
  }
  // Confirm before proceeding with an htmx request
  el.addEventListener("htmx:confirm", function (e) {
    e.preventDefault()
    Swal.fire({
      title: "Proceed?",
      text: e.detail.question,
      showCancelButton: true,
      confirmButtonText: "Delete",
    }).then(function (result) {
      if (result.isConfirmed) {
        e.detail.issueRequest(true) // use true to skip window.confirm
      }
    })
  })
}

// Set the avatar image preview (in user settings)
function setAvatarImage(avatar_upload_id, avatar_url_id) {
  const imgPreview = document.getElementById("avatar-image")
  const chooseFile = document.getElementById(avatar_upload_id)
  const remoteFile = document.getElementById(avatar_url_id)

  const files = chooseFile.files[0]
  if (files) {
    const fileReader = new FileReader()
    fileReader.readAsDataURL(files)
    fileReader.addEventListener("load", function () {
      imgPreview.innerHTML =
        '<img src="' + this.result + '" class="object-cover h-36 w-36" />'
    })
  } else if (remoteFile.value) {
    imgPreview.innerHTML =
      '<img src="' + remoteFile.value + '" class="object-cover h-36 w-36" />'
  }
}
