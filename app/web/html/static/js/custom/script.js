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

function lazyLoadVideos() {
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
}
document.addEventListener("DOMContentLoaded", lazyLoadVideos)

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

// Set the thumbnail image preview (in Blog edit)
function setThumbnailImage() {
  const imgPreview = document.getElementById("thumbnail-image")
  const remoteFile = document.getElementById("{{ form.thumbnail_url.id }}")
  if (remoteFile.value) {
    imgPreview.innerHTML =
      '<img src="' +
      remoteFile.value +
      '" class="object-cover max-w-lg max-h-36" />'
  }
}

var formSubmitting = false
function setFormSubmitting() {
  formSubmitting = true
}

// Prompt the user before leaving the page if there are unsaved changes (in Blog edit)
function promptForExit(event, isDirty) {
  if (formSubmitting || !isDirty) {
    return undefined
  }

  const confirmationMessage = "Any unsaved changes will be lost."

  event.returnValue = confirmationMessage //Gecko + IE
  return confirmationMessage //Gecko + Webkit, Safari, Chrome etc.
}

// Copy the text to the input field (in Blog comments)
function copyToInput(text, inputId) {
  // Get the input field
  const inputField = document.getElementById(inputId)

  let textVal = text

  // URL decode the text
  textVal = decodeURIComponent(textVal)

  // Replace newline characters with "\n> "
  textVal = textVal.replace(/\n/g, "\n> ")

  // Trim trailing "\n> " strings
  textVal = textVal.replace(/\n> $/g, "")

  // Copy the text to the input field
  inputField.value = `> ${textVal}\n\n`

  // Scroll the screen to the input field smoothly
  inputField.scrollIntoView({ behavior: "smooth" })

  // Delay the focus for the duration of the scroll animation
  setTimeout(function () {
    inputField.focus()
  }, 700)

  // Set the cursor to the end of the input field
  // Delay the focus for the duration of the scroll animation
  setTimeout(function () {
    inputField.selectionStart = inputField.selectionEnd =
      inputField.value.length
  }, 710)
}

function performKeyMapAction(input, event) {
  const keyBindingMap = {
    "ctrl+b": { func: flank, args: ["**"] },
    "ctrl+i": { func: flank, args: ["*"] },
    "ctrl+s": { func: flank, args: ["~~"] },
    "`": { func: flank, args: ["`"] },
    "'": { func: flank, args: ["'"] },
    '"': { func: flank, args: ['"'] },
    "(": { func: flank, args: ["(", ")"] },
    "{": { func: flank, args: ["{", "}"] },
    "[": { func: flank, args: ["[", "]"] },
    "*": { func: flank, args: ["*"] },
    _: { func: flank, args: ["_"] },
    "~": { func: flank, args: ["~"] },
    "ctrl+'": { func: addPrefixToLine, args: ["> "] },
  }
  const pressedKey = getPressedKey(input, event)
  const keyMapValue = keyBindingMap[pressedKey]

  if (!keyMapValue) return

  const textInfo = getInputs(input)

  const { func, args } = keyMapValue
  func(input, event, textInfo, ...args)
}

function getPressedKey(input, event) {
  let pressedKey = event.key
  if (event.ctrlKey) {
    pressedKey = `ctrl+${pressedKey}`
  }
  return pressedKey
}

function getInputs(input) {
  const cursorStart = input.selectionStart
  const cursorEnd = input.selectionEnd
  const text = input.value
  const beforeText = text.substring(0, cursorStart)
  const selectedText = text.substring(cursorStart, cursorEnd)
  const afterText = text.substring(cursorEnd)
  return { cursorStart, cursorEnd, text, beforeText, selectedText, afterText }
}

function addPrefixToLine(input, event, textInfo, prefix) {
  const cursorPosition = input.selectionStart
  const beforeCursor = input.value.substring(0, cursorPosition)
  const afterCursor = input.value.substring(cursorPosition)

  // Find the start of the line
  const lineStart = beforeCursor.lastIndexOf("\n") + 1

  // Add the prefix to the start of the line
  const newValue =
    beforeCursor.substring(0, lineStart) +
    prefix +
    beforeCursor.substring(lineStart) +
    afterCursor

  // Update the input value
  input.value = newValue

  // Move the cursor to its original position
  input.selectionStart = input.selectionEnd = cursorPosition + prefix.length // "+ prefix.length" because we added the prefix
}

function flank(input, event, textInfo, left, right) {
  if (textInfo.cursorStart === textInfo.cursorEnd) return
  event.preventDefault()

  let leftChar = left
  let rightChar = right
  if (!rightChar) {
    rightChar = leftChar
  }

  input.value = `${textInfo.beforeText}${leftChar}${textInfo.selectedText}${rightChar}${textInfo.afterText}`

  // Keep the original highlighted text highlighted
  input.selectionStart = textInfo.cursorStart + leftChar.length
  input.selectionEnd = textInfo.cursorEnd + rightChar.length
}
