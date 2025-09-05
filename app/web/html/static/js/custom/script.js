// Push a notification message to the screen
function pushNotify(title, text = "", status = "success", autotimeout = 3000) {
  // Bottom right position is sometimes offscreen on mobile
  // Use top center position for mobile and right bottom for desktop
  let position
  if (window.innerWidth <= 768) {
    position = "top center"
  } else {
    position = "right bottom"
  }
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
    position: position,
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

// Add freezeframe.js to GIFs
// https://github.com/ctrl-freaks/freezeframe.js/tree/master/packages/freezeframe
function addFreezeFrame() {
  const allGifs = document.querySelectorAll('img[src$=".gif"]')
  ;[...allGifs].forEach((gif) => {
    new Freezeframe({
      selector: gif,
      trigger: "click",
      overlay: true,
      responsive: false,
    })
  })
}

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

function escapeHTML(str) {
  const div = document.createElement("div")
  div.appendChild(document.createTextNode(str))
  return div.innerHTML
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
        '<img src="' +
        escapeHTML(this.result) +
        '" class="object-cover h-36 w-36" />'
    })
  } else if (remoteFile.value) {
    imgPreview.innerHTML =
      '<img src="' +
      escapeHTML(remoteFile.value) +
      '" class="object-cover h-36 w-36" />'
  }
}

// Set the thumbnail image preview (in Blog edit)
function setThumbnailImage() {
  const imgPreview = document.getElementById("thumbnail-image")
  const remoteFile = document.getElementById("{{ form.thumbnail_url.id }}")
  if (remoteFile.value) {
    imgPreview.innerHTML =
      '<img src="' +
      escapeHTML(remoteFile.value) +
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

function mdTextareaKeyPress(
  textareaElement,
  event,
  historyManager,
  charCount = 0
) {
  performKeyMapAction(textareaElement, event, historyManager)
  setTimeout(() => {
    updateCharCount(
      textareaElement,
      document.getElementById("textarea-char-count"),
      charCount
    )
  }, 0)
  historyManager.saveState(textareaElement, event)
}

function updateCharCount(textareaElement, containerElement, maxCharCount) {
  if (!maxCharCount) return
  const textareaCharCount = textareaElement.value.length
  const result = `${textareaCharCount} / ${maxCharCount}`
  containerElement.textContent = result
}

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
  "ctrl+l": { func: addLink, args: [] },
  "ctrl+'": { func: addPrefixToLine, args: ["> "] },
  "ctrl+q": { func: addPrefixToLine, args: ["> "] },
  "ctrl+u": { func: addPrefixToLine, args: ["- "] },
  "ctrl+o": { func: addPrefixToLine, args: ["1. "] },
  "ctrl+d": { func: deleteLine, args: [] },
  "ctrl+z": { func: "undo", args: [] },
  "ctrl+shift+z": { func: "redo", args: [] },
  "ctrl+y": { func: "redo", args: [] },
}

function performKeyMapAction(textareaElement, event, historyManager) {
  const pressedKey = getPressedKey(event)
  const keyMapValue = keyBindingMap[pressedKey]

  if (!keyMapValue) return

  const { func, args } = keyMapValue
  // if keyMapValue is a string, it's a historyManager method
  if (typeof func === "string") {
    historyManager[func](textareaElement, event, ...args)
    return
  }
  func(textareaElement, event, ...args)
}

function getPressedKey(event) {
  let pressedKey = event.key.toLowerCase()
  if (event.ctrlKey) {
    if (event.shiftKey) {
      pressedKey = `ctrl+shift+${pressedKey}`
    } else {
      pressedKey = `ctrl+${pressedKey}`
    }
  }
  return pressedKey
}

function addPrefixToLine(textareaElement, event, prefix, trimIfSame = false) {
  event.preventDefault()

  const value = textareaElement.value
  const selStart = textareaElement.selectionStart
  const selEnd = textareaElement.selectionEnd
  let prefixValue = prefix

  // Find the start of the first selected line and end of the last selected line
  const firstLineStart = value.lastIndexOf("\n", selStart - 1) + 1
  let lastLineEnd = value.indexOf("\n", selEnd)
  if (lastLineEnd === -1) lastLineEnd = value.length

  // Get the selected block
  const selectedBlock = value.substring(firstLineStart, lastLineEnd)
  // Split into lines
  const lines = selectedBlock.split("\n")

  // Add prefix to each line
  const newLines = lines.map((line) => {
    let p = prefixValue
    if (trimIfSame && line[0] === prefixValue[0]) {
      p = prefixValue.trim()
    }
    return p + line
  })
  const newBlock = newLines.join("\n")

  // Build the new value
  const newValue =
    value.substring(0, firstLineStart) + newBlock + value.substring(lastLineEnd)

  // Update the textarea value
  textareaElement.value = newValue

  // Calculate new selection range
  // The selection should cover all the newly prefixed lines
  const newSelStart = firstLineStart
  const newSelEnd = firstLineStart + newBlock.length
  textareaElement.selectionStart = newSelStart
  textareaElement.selectionEnd = newSelEnd

  // Focus the textarea element
  textareaElement.focus()
}

function flank(textareaElement, event, left, right, requireHighlighted = true) {
  const textInfo = getTextInfo(textareaElement)
  if (textInfo.cursorStart === textInfo.cursorEnd && requireHighlighted) return
  event.preventDefault()

  let leftChar = left
  let rightChar = right
  if (!rightChar) {
    rightChar = leftChar
  }

  textareaElement.value = `${textInfo.beforeText}${leftChar}${textInfo.selectedText}${rightChar}${textInfo.afterText}`

  // Keep the original highlighted text highlighted
  textareaElement.selectionStart = textInfo.cursorStart + leftChar.length
  textareaElement.selectionEnd = textInfo.cursorEnd + rightChar.length

  // Focus the textarea element
  textareaElement.focus()

  // Dispatch an input event to indicate the value has changed
  const newInputEvent = new Event("input", { bubbles: true, cancelable: true })
  textareaElement.dispatchEvent(newInputEvent)
}

function addLink(textareaElement, event) {
  event.preventDefault()

  const textInfo = getTextInfo(textareaElement)
  const linkText = textInfo.selectedText || "Link text"
  const linkUrl = "https://example.com"

  const newValue = `${textInfo.beforeText}[${linkText}](${linkUrl})${textInfo.afterText}`
  textareaElement.value = newValue

  // Calculate the start and end positions of the linkUrl
  const linkUrlStart = textInfo.cursorStart + linkText.length + 3
  const linkUrlEnd = linkUrlStart + linkUrl.length

  // Highlight the linkUrl
  textareaElement.selectionStart = linkUrlStart
  textareaElement.selectionEnd = linkUrlEnd

  // Focus the textarea element
  textareaElement.focus()
}

function deleteLine(textareaElement, event) {
  event.preventDefault()

  const value = textareaElement.value
  const selStart = textareaElement.selectionStart
  const selEnd = textareaElement.selectionEnd

  // If nothing is selected, treat as single line delete
  if (selStart === selEnd) {
    // Find the start and end of the line
    const lineStart = value.lastIndexOf("\n", selStart - 1) + 1
    let lineEnd = value.indexOf("\n", selStart)
    if (lineEnd === -1) lineEnd = value.length

    const newValue =
      value.substring(0, lineStart) + value.substring(lineEnd + 1)
    textareaElement.value = newValue
    // Move cursor to start of the next line (or end of text)
    textareaElement.selectionStart = textareaElement.selectionEnd = lineStart
    textareaElement.focus()
    return
  }

  // If there is a selection, delete all lines that intersect with the selection
  // Expand selection to start of first line and end of last line
  const firstLineStart = value.lastIndexOf("\n", selStart - 1) + 1
  let lastLineEnd = value.indexOf("\n", selEnd)
  if (lastLineEnd === -1) lastLineEnd = value.length
  else lastLineEnd = lastLineEnd + 1 // include the newline

  const newValue =
    value.substring(0, firstLineStart) + value.substring(lastLineEnd)
  textareaElement.value = newValue
  // Place cursor at start of where the deleted block was
  textareaElement.selectionStart = textareaElement.selectionEnd = firstLineStart
  textareaElement.focus()
}

function getTextAndCursorPosition(textareaElement) {
  const cursorStart = textareaElement.selectionStart
  const cursorEnd = textareaElement.selectionEnd
  const text = textareaElement.value
  return { cursorStart, cursorEnd, text }
}

function getTextInfo(textareaElement) {
  const { cursorStart, cursorEnd, text } =
    getTextAndCursorPosition(textareaElement)
  const beforeText = text.substring(0, cursorStart)
  const selectedText = text.substring(cursorStart, cursorEnd)
  const afterText = text.substring(cursorEnd)
  return { cursorStart, cursorEnd, text, beforeText, selectedText, afterText }
}

class TextAreaHistoryManager {
  constructor() {
    this.history = []
    this.currentPosition = -1
  }

  saveState(textareaElement, event) {
    const state = {
      value: textareaElement.value,
      cursorStart: textareaElement.selectionStart,
      cursorEnd: textareaElement.selectionEnd,
    }
    const previousState = this.history[this.currentPosition]
    // Return early if state is not different from the previous state
    if (
      previousState &&
      previousState.value === state.value &&
      previousState.cursorStart === state.cursorStart &&
      previousState.cursorEnd === state.cursorEnd
    ) {
      return
    }

    // Remove states after current position to discard redos when a new state is saved
    this.history = this.history.slice(0, this.currentPosition + 1)
    this.history.push(state)
    this.currentPosition++

    // Limit history to 25 states
    if (this.history.length > 25) {
      this.history.shift() // remove the oldest state
      this.currentPosition-- // adjust the current position
    }
  }

  undo(textareaElement, event) {
    event.preventDefault()
    if (this.currentPosition <= 0) {
      return
    }
    this.currentPosition--
    const state = this.history[this.currentPosition]
    textareaElement.value = state.value
    textareaElement.selectionStart = state.cursorStart
    textareaElement.selectionEnd = state.cursorEnd

    // Focus the textarea element
    textareaElement.focus()
  }

  redo(textareaElement, event) {
    event.preventDefault()
    if (this.currentPosition >= this.history.length - 1) {
      return
    }
    this.currentPosition++
    const state = this.history[this.currentPosition]
    textareaElement.value = state.value
    textareaElement.selectionStart = state.cursorStart
    textareaElement.selectionEnd = state.cursorEnd

    // Focus the textarea element
    textareaElement.focus()
  }
}
