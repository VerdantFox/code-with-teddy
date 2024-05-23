// -----------------------------------------------------------------------
// Helper functions
// -----------------------------------------------------------------------
function pickRandom(array) {
  return array[Math.floor(Math.random() * array.length)]
}

function capitalizeFirstLetter(string) {
  return string.charAt(0).toUpperCase() + string.slice(1)
}

function copyPlayer(player) {
  return new Player(
    player.number,
    player.color,
    player.isAI,
    player.depth,
    player.wins,
    player.losses,
    player.ties
  )
}

function attrOrDefault(attr, defaultValue) {
  return attr === undefined ? defaultValue : attr
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function allEqual(arr) {
  return arr.every((element) => element === arr[0])
}

function gridPoint(column, row) {
  return { column: column, row: row }
}

function updateGrid(grid, column, row, player) {
  grid[column][row] = player
  return grid
}

function colHistoryAndGrid(colHistory, grid) {
  return { colHistory: colHistory, grid: grid }
}

function makeGrid(columns, rows) {
  const grid = []
  for (let column = 0; column < columns; column++) {
    grid[column] = []
    for (let row = 0; row < rows; row++) {
      grid[column][row] = null
    }
  }
  return grid
}

function topRow(grid, column) {
  for (let row = grid[0].length - 1; row > -1; row--) {
    if (grid[column][row] === null) {
      return row
    }
  }
  return null // Column is full
}

const medCopy = (arr) => {
  const copy = []
  arr.forEach((elem) => {
    copy.push(Array.isArray(elem) ? medCopy(elem) : elem)
  })
  return copy
}

function distFromMid(column) {
  return Math.abs(column - 3)
}

// -----------------------------------------------------------------------
// Classes
// -----------------------------------------------------------------------
class Player {
  constructor(number, color) {
    this.number = number
    this.color = color
    this.lastMove = null
    this.wins = 0
    this.losses = 0
    this.draws = 0
    this.lastGame = null
    this.description = document.querySelector(`#${this.color}-description`)
    this.pic = document.querySelector(`#${this.color}-pic`)
    this.winCounter = document.querySelector(`#${this.color}-wins`)
    this.loseCounter = document.querySelector(`#${this.color}-losses`)
    this.drawCounter = document.querySelector(`#${this.color}-draws`)
    this.isComputerSetting = document.querySelector(`#${this.color}-switch`)
    this.depthSetting = document.querySelector(`#${this.color}-depth`)
    this.depthDisplay = document.querySelector(`#${this.color}-depth-display`)
    this.autoMoveSetting = document.querySelector(`#${this.color}-auto-move`)
    this.moveButton = document.querySelector(`#${this.color}-move-button`)
    this.autoMove = this.autoMoveSetting.checked
    this.setIsAI(this.isComputerSetting.checked)
    this.depth = parseInt(this.depthSetting.value)
    this.setDepthDisplay()

    this.depthSetting.addEventListener("change", () => {
      this.depth = parseInt(this.depthSetting.value)
      this.depthDisplay.textContent = this.depthSetting.value
    })

    this.isComputerSetting.addEventListener("change", () => {
      this.setIsAI(this.isComputerSetting.checked)
    })

    this.autoMoveSetting.addEventListener("change", () => {
      this.setIsAutomove(this.autoMoveSetting.checked)
    })
  }

  setIsAI(isAI) {
    this.isAI = isAI
    if (isAI) {
      this.type = "computer"
      this.avatar = "robot"
      this.moveButton.disabled = this.autoMove
    } else {
      this.type = "human"
      this.avatar = "fox"
      this.moveButton.disabled = true
    }
    this.setDescriptionType()
    this.setImageSrc()
  }

  setIsAutomove(autoMove) {
    this.autoMove = autoMove
    this.moveButton.disabled = autoMove
  }

  setImageSrc() {
    this.pic.src = `/static/media/connect4/${this.avatar}-${this.color}.png`
  }

  setDescriptionType() {
    this.description.textContent = this.type
  }

  setDepthDisplay() {
    this.depthDisplay.textContent = this.depth
  }

  updateWLD() {
    this.winCounter.classList.remove("font-weight-bold", "border")
    this.loseCounter.classList.remove("font-weight-bold", "border")
    this.drawCounter.classList.remove("font-weight-bold", "border")
    this.winCounter.textContent = this.wins
    this.loseCounter.textContent = this.losses
    this.drawCounter.textContent = this.draws
    document
      .querySelector(`#${this.color}-${this.lastGame}`)
      .classList.add("font-weight-bold", "border")
  }
}

class AI {
  constructor(player, opponent, board) {
    this.player = player
    this.opponent = opponent
    this.board = board
    this.depth = parseInt(player.depth)
    this.selectedMove = null
  }

  updateMoveWeights(moveWeights) {
    for (let column = 0; column < this.board.columns; column++) {
      const weightElem = document.querySelector(`#ai-weight-${column}`)
      weightElem.classList.remove(
        "mw-green",
        "mw-red",
        "mw-yellow",
        "mw-selected"
      )
      weightElem.innerHTML = "&nbsp;"
    }
    if (!moveWeights) return
    Object.keys(moveWeights).forEach((key) => {
      const val = moveWeights[key]
      const roundedVal = Math.round(val)
      const weightElem = document.querySelector(`#ai-weight-${key}`)
      weightElem.textContent = roundedVal
      if (roundedVal > 0) {
        weightElem.classList.add("mw-green")
      } else if (roundedVal < 0) {
        weightElem.classList.add("mw-red")
      } else {
        weightElem.classList.add("mw-yellow")
      }
    })
    document
      .querySelector(`#ai-weight-${this.selectedMove}`)
      .classList.add("mw-selected")
  }

  getAvailableMoves(grid) {
    const availableMoves = []
    for (let column = 0; column < this.board.columns; column++) {
      if (topRow(grid, column) !== null) {
        availableMoves.push(column)
      }
    }
    return availableMoves
  }

  getBestMoves(weights) {
    let bestWeight = -Infinity
    let bestMoves = []
    for (const column in weights) {
      if (weights[column] > bestWeight) {
        bestWeight = weights[column]
        bestMoves = [column]
      } else if (weights[column] === bestWeight) {
        bestMoves.push(column)
      }
    }
    return bestMoves
  }

  getBestMove(weights) {
    const bestMoves = this.getBestMoves(weights)
    let lowestAbsoluteColumn = Infinity
    let lowestMoves = []
    for (const move of bestMoves) {
      const minus3Abs = distFromMid(move)
      if (minus3Abs < lowestAbsoluteColumn) {
        lowestAbsoluteColumn = minus3Abs
        lowestMoves = [move]
      } else if (minus3Abs === lowestAbsoluteColumn) {
        lowestMoves.push(move)
      }
    }
    this.selectedMove = pickRandom(lowestMoves)
    return this.selectedMove
  }

  getMove() {
    this.selectedMove = null
    let turn = this.player
    const baseAvailableMoves = this.getAvailableMoves(this.board.grid)
    if (baseAvailableMoves.includes(3) && this.depth > 4) {
      this.depth = 4
    }
    if (this.board.nbrOfMoves === 3 && this.player.depth < 4) {
      const middleMoves = medCopy(baseAvailableMoves)
      middleMoves.pop()
      middleMoves.shift()
      middleMoves.pop()
      middleMoves.shift()
      for (const column of middleMoves) {
        if (!this.board.grid[column][this.board.rows - 1]) {
          this.updateMoveWeights(null)
          return column
        }
      }
    }
    let roundWeight = baseAvailableMoves.length ** this.depth
    const weights = {}
    baseAvailableMoves.forEach((column) => {
      weights[column] = 0
    })
    if (this.depth === 0) {
      this.selectedMove = this.getBestMove(weights)
      this.updateMoveWeights(weights)
      return this.selectedMove
    }
    let isRound1Win = false
    const newColGrids = []
    for (const column of baseAvailableMoves) {
      const row = topRow(this.board.grid, column)
      const innerGrid = medCopy(this.board.grid)
      updateGrid(innerGrid, column, row, turn)
      const winnerAndPoints = new Board(innerGrid).checkForWin()
      if (winnerAndPoints) {
        isRound1Win = true
        weights[column] += roundWeight
      }
      newColGrids.push(colHistoryAndGrid([column], innerGrid))
    }
    if (isRound1Win) {
      this.selectedMove = this.getBestMove(weights)
      this.updateMoveWeights(weights)
      return this.selectedMove
    }
    let colGrids = [...newColGrids]
    for (let round = 2; round <= this.depth; round++) {
      turn = turn === this.player ? this.opponent : this.player
      colGrids = [...newColGrids]
      newColGrids.length = 0
      for (const colGrid of colGrids) {
        const baseColumn = colGrid.colHistory[0]
        const outerGrid = colGrid.grid
        const availableMoves = this.getAvailableMoves(outerGrid)
        for (const column of availableMoves) {
          let missedWin = false
          const row = topRow(outerGrid, column)
          const innerGrid = medCopy(outerGrid)
          const colHistory = [...colGrid.colHistory, column]
          updateGrid(innerGrid, column, row, turn)
          const winnerAndPoints =
            round === 2
              ? new Board(innerGrid).checkForWin()
              : new Board(innerGrid).checkForNonVertWin()
          if (
            round !== 2 &&
            winnerAndPoints &&
            colHistory[2] === baseColumn &&
            colHistory[1] !== baseColumn
          ) {
            missedWin = true
          }
          if (winnerAndPoints) {
            if (missedWin) {
              weights[baseColumn] -= roundWeight + 1
            } else if (winnerAndPoints.winner === this.opponent) {
              weights[baseColumn] -= roundWeight
            } else {
              weights[baseColumn] += roundWeight
            }
          } else {
            newColGrids.push(colHistoryAndGrid(colHistory, innerGrid))
          }
        }
      }
      if (round === 2) {
        const bestMoves = this.getBestMoves(weights)
        if (bestMoves.length === 1) {
          this.selectedMove = bestMoves[0]
          this.updateMoveWeights(weights)
          return this.selectedMove
        }
      }
      roundWeight /= baseAvailableMoves.length
    }
    this.selectedMove = this.getBestMove(weights)
    this.updateMoveWeights(weights)
    return this.selectedMove
  }
}

class Board {
  constructor(grid) {
    this.columns = 7
    this.rows = 6
    this.grid = grid || makeGrid(this.columns, this.rows)
    this.nbrOfMoves = 0
  }

  topRow(column) {
    return topRow(this.grid, column)
  }

  updateGrid(column, row, player) {
    return updateGrid(this.grid, column, row, player)
  }

  getCircleOwners(arr) {
    return arr.map((point) => this.grid[point.column][point.row])
  }

  getWinner(arr) {
    return arr[0] === null ? null : allEqual(arr) ? arr[0] : null
  }

  getWinnerAndPoints(points) {
    const circleOwners = this.getCircleOwners(points)
    const winner = this.getWinner(circleOwners)
    return { winner: winner, points: points }
  }

  checkHorizontalWin(column, row) {
    const points = [
      gridPoint(column, row),
      gridPoint(column + 1, row),
      gridPoint(column + 2, row),
      gridPoint(column + 3, row),
    ]
    return this.getWinnerAndPoints(points)
  }

  checkVerticalWin(column, row) {
    const points = [
      gridPoint(column, row),
      gridPoint(column, row + 1),
      gridPoint(column, row + 2),
      gridPoint(column, row + 3),
    ]
    return this.getWinnerAndPoints(points)
  }

  checkDiagonalWinNWSE(column, row) {
    const points = [
      gridPoint(column, row),
      gridPoint(column + 1, row + 1),
      gridPoint(column + 2, row + 2),
      gridPoint(column + 3, row + 3),
    ]
    return this.getWinnerAndPoints(points)
  }

  checkDiagonalWinSWNE(column, row) {
    const points = [
      gridPoint(column, row),
      gridPoint(column + 1, row - 1),
      gridPoint(column + 2, row - 2),
      gridPoint(column + 3, row - 3),
    ]
    return this.getWinnerAndPoints(points)
  }

  checkForNonVertWin() {
    for (let column = 0; column < this.columns - 3; column++) {
      for (let row = 0; row < this.rows; row++) {
        const winnerAndPoints = this.checkHorizontalWin(column, row)
        if (winnerAndPoints.winner) {
          return winnerAndPoints
        }
      }
    }
    for (let column = 0; column < this.columns - 3; column++) {
      for (let row = 0; row < this.rows - 3; row++) {
        const winnerAndPoints = this.checkDiagonalWinNWSE(column, row)
        if (winnerAndPoints.winner) {
          return winnerAndPoints
        }
      }
    }
    for (let column = 0; column < this.columns - 3; column++) {
      for (let row = 3; row < this.rows + 3; row++) {
        const winnerAndPoints = this.checkDiagonalWinSWNE(column, row)
        if (winnerAndPoints.winner) {
          return winnerAndPoints
        }
      }
    }
    return null
  }

  checkForWin() {
    for (let column = 0; column < this.columns - 3; column++) {
      for (let row = 0; row < this.rows; row++) {
        const winnerAndPoints = this.checkHorizontalWin(column, row)
        if (winnerAndPoints.winner) {
          return winnerAndPoints
        }
      }
    }
    for (let column = 0; column < this.columns; column++) {
      for (let row = 0; row < this.rows - 3; row++) {
        const winnerAndPoints = this.checkVerticalWin(column, row)
        if (winnerAndPoints.winner) {
          return winnerAndPoints
        }
      }
    }
    for (let column = 0; column < this.columns - 3; column++) {
      for (let row = 0; row < this.rows - 3; row++) {
        const winnerAndPoints = this.checkDiagonalWinNWSE(column, row)
        if (winnerAndPoints.winner) {
          return winnerAndPoints
        }
      }
    }
    for (let column = 0; column < this.columns - 3; column++) {
      for (let row = 3; row < this.rows + 3; row++) {
        const winnerAndPoints = this.checkDiagonalWinSWNE(column, row)
        if (winnerAndPoints.winner) {
          return winnerAndPoints
        }
      }
    }
    return null
  }

  checkForTie() {
    return this.grid.every((column) => column[0] !== null)
  }
}

class Game {
  constructor(player1, player2, gamesPlayed) {
    this.board = new Board()
    this.gamesPlayed = attrOrDefault(gamesPlayed, 0)
    this.player1 = player1 || new Player(1, "red")
    this.player2 = player2 || new Player(2, "blue")
    new AI(this.player1, this.player2, this.board).updateMoveWeights(false)
    this.players = [this.player1, this.player2]
    this.turn = this.player1
    this.notTurn = this.player2
    this.gameOver = false
    this.winner = null
    this.loser = null
    this.points = null
    this.boardHTML = document.querySelector("#board")
    this.message = document.querySelector("#message")
    this.autoResetSetting = document.querySelector("#auto-reset-switch")
    this.totalGamesSetting = document.querySelector("#total-games")
    this.showAIMoveWeightsSetting = document.querySelector(
      "#show-move-weights-switch"
    )
    this.showAnimationsSetting = document.querySelector(
      "#show-move-animations-switch"
    )
    this.aiMoveWeightsRow = document.querySelector("#ai-move-weights-row")
    this.resetScoreButton = document.querySelector("#reset-score")
    this.runStartupFunctions()
  }

  runStartupFunctions() {
    this.updateMessage(
      `New game! ${capitalizeFirstLetter(this.turn.color)}'s turn...`
    )
    this.addClicks()
    this.paintBoard()
    this.updateAvatars()
    this.getSettings()
    this.createEvents()
    if (this.player1.isAI) {
      this.nextMove()
    }
  }

  getSettings() {
    this.autoReset = this.autoResetSetting.checked
    this.totalGamesSettingVal = parseInt(this.totalGamesSetting.value)
    this.setShowAIMoveWeights(this.showAIMoveWeightsSetting.checked)
    this.showAnimations = this.showAnimationsSetting.checked
  }

  createEvents() {
    this.players.forEach((player) => {
      player.lastMove = null
      player.isComputerSetting.addEventListener("change", () => {
        if (
          player === this.turn &&
          player.isComputerSetting.checked &&
          player.autoMove
        ) {
          this.nextMove()
        }
      })
      player.moveButton.addEventListener("click", () => {
        if (player.isAI && player === this.turn) {
          this.AiMove()
        }
      })
      player.autoMoveSetting.addEventListener("change", () => {
        if (player.isAI && player === this.turn) {
          this.AiMove()
        }
      })
    })
    this.autoResetSetting.addEventListener("change", () => {
      this.autoReset = this.autoResetSetting.checked
    })
    this.totalGamesSetting.addEventListener("keyup", () => {
      this.totalGamesSettingVal = parseInt(this.totalGamesSetting.value)
    })
    this.showAIMoveWeightsSetting.addEventListener("change", () => {
      this.setShowAIMoveWeights(this.showAIMoveWeightsSetting.checked)
    })
    this.showAnimationsSetting.addEventListener("change", () => {
      this.showAnimations = this.showAnimationsSetting.checked
    })
    this.resetScoreButton.addEventListener("click", () => {
      this.resetScore()
    })
  }

  async updateMessage(message) {
    this.message.textContent = message
  }

  setShowAIMoveWeights(show) {
    this.boardHTML.classList.remove("mb-4")
    if (show) {
      this.aiMoveWeightsRow.style.display = ""
    } else {
      this.aiMoveWeightsRow.style.display = "none"
      this.boardHTML.classList.add("mb-4")
    }
  }

  async paintWin(points) {
    for (const point of points) {
      const circle = document.querySelector(
        `#circle-${point.column}-${point.row}`
      )
      const winColor = `color-${this.winner.color}-win`
      circle.classList.add(winColor)
    }
  }

  async paintChosen(column, row) {
    const lastCircleHtml = document.querySelector(`#circle-${column}-${row}`)
    lastCircleHtml.classList.add("chosen")
  }

  async paintBoard() {
    for (let column = 0; column < this.board.columns; column++) {
      for (let row = 0; row < this.board.rows; row++) {
        const circleHtml = document.querySelector(`#circle-${column}-${row}`)
        circleHtml.className = "circles cursor-pointer"
        const circlePlayer = this.board.grid[column][row]
        if (circlePlayer !== null) {
          circleHtml.classList.add(`color-${circlePlayer.color}`)
        }
      }
    }
    if (this.turn.lastMove) {
      this.paintChosen(this.turn.lastMove.column, this.turn.lastMove.row)
    }
    if (this.winner) {
      this.paintWin(this.points)
    }
    await sleep(0)
  }

  async updateAvatars() {
    this.turn.pic.classList.add("active-player")
    this.notTurn.pic.classList.remove("active-player")
  }

  getLoser() {
    this.loser = this.winner === this.player1 ? this.player2 : this.player1
  }

  updateWLD() {
    this.getLoser()
    if (this.winner) {
      this.winner.wins += 1
      this.winner.lastGame = "wins"
      this.loser.losses += 1
      this.loser.lastGame = "losses"
    } else {
      this.player1.draws += 1
      this.player2.draws += 1
      this.player1.lastGame = "draws"
      this.player2.lastGame = "draws"
    }
    this.player1.updateWLD()
    this.player2.updateWLD()
  }

  async alternateTurn() {
    ;[this.turn, this.notTurn] = [this.notTurn, this.turn]
    this.updateAvatars()
  }

  async animateMove(column, row) {
    if (!this.showAnimations) return
    let currentRow = 0
    while (currentRow < row) {
      const circleHtml = document.querySelector(
        `#circle-${column}-${currentRow}`
      )
      const color = `color-${this.turn.color}`
      circleHtml.classList.add(color)
      await sleep(50)
      circleHtml.classList.remove(color)
      currentRow++
    }
  }

  async AiMove() {
    if (this.gameOver) return
    const ai = new AI(this.turn, this.notTurn, this.board)
    const column = ai.getMove()
    this.makeMove(column)
  }

  async checkResetGame() {
    const maxGames =
      parseInt(this.totalGamesSettingVal) === 0
        ? Infinity
        : this.totalGamesSettingVal
    await sleep(500)
    if (this.autoReset && this.gamesPlayed < maxGames) {
      resetGame()
    }
  }

  async nextMove() {
    if (this.turn.isAI) {
      await this.removeClicks()
      if (this.turn.autoMove) {
        await this.AiMove()
      }
    } else {
      await this.addClicks()
    }
  }

  async makeMove(column) {
    if (this.gameOver) return
    const row = this.board.topRow(column)
    if (row === null) {
      this.nextMove()
      return
    }
    await this.animateMove(column, row)
    this.board.updateGrid(column, row, this.turn)
    this.turn.lastMove = gridPoint(column, row)
    if (this.board.checkForTie()) {
      this.gameOver = true
      this.updateMessage("It's a tie!")
    }
    const winnerAndPoints = this.board.checkForWin()
    if (winnerAndPoints) {
      this.gameOver = true
      this.winner = winnerAndPoints.winner
      this.points = winnerAndPoints.points
      this.updateMessage(`${capitalizeFirstLetter(this.winner.color)} wins!`)
    }
    if (this.gameOver) {
      this.gamesPlayed += 1
      this.updateWLD()
      await this.checkResetGame()
    }
    this.paintBoard()
    if (!this.gameOver) {
      await this.alternateTurn()
      this.updateMessage(`${capitalizeFirstLetter(this.turn.color)}'s turn...`)
      await sleep(100)
      this.board.nbrOfMoves += 1
      this.nextMove()
    }
  }

  async removeClicks() {
    document.querySelectorAll(".circles").forEach((circle) => {
      circle.onclick = null
    })
  }

  async addClicks() {
    document.querySelectorAll(".circles").forEach((circle) => {
      const circleID = circle.id
      const column = parseInt(circleID.split("-")[1])
      circle.onclick = async () => {
        await this.removeClicks()
        await this.makeMove(column)
      }
    })
  }

  resetScore() {
    this.gamesPlayed = 0
    this.players.forEach((player) => {
      player.wins = 0
      player.losses = 0
      player.draws = 0
      player.lastGame = null
      player.updateWLD()
    })
  }
}

// -----------------------------------------------------------------------
// Start Script
// -----------------------------------------------------------------------
let game = new Game()
const resetGame = () => {
  game.gameOver = true
  game.nextMove()
  game = new Game(game.player1, game.player2, game.gamesPlayed)
  game.paintBoard()
}

document.querySelector("#reset-board").addEventListener("click", () => {
  resetGame()
})
