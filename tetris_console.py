#!/usr/bin/env python3
"""
Tetris für die Linux-Konsole (ncurses)

Speichern als: tetris_console.py
Ausführen: python3 tetris_console.py

Controls:
  ← / h : Move left
  → / l : Move right
  ↓ / j : Soft drop
  space  : Hard drop
  z / x  : Rotate (z = left, x = right)
  p      : Pause
  q      : Quit

Kompatibel mit Python 3.8+
"""
import curses
import random
import time
import sys

BOARD_WIDTH = 10
BOARD_HEIGHT = 20

TETROMINOES = {
    'I': [[0,0,0,0], [1,1,1,1], [0,0,0,0], [0,0,0,0]],
    'J': [[1,0,0],[1,1,1],[0,0,0]],
    'L': [[0,0,1],[1,1,1],[0,0,0]],
    'O': [[1,1],[1,1]],
    'S': [[0,1,1],[1,1,0],[0,0,0]],
    'T': [[0,1,0],[1,1,1],[0,0,0]],
    'Z': [[1,1,0],[0,1,1],[0,0,0]],
}

COLORS = {
    'I': 6,
    'J': 4,
    'L': 3,
    'O': 2,
    'S': 5,
    'T': 1,
    'Z': 7,
}


class Piece:
    def __init__(self, shape):
        self.shape = shape
        self.matrix = [row[:] for row in TETROMINOES[shape]]
        self.h = len(self.matrix)
        self.w = len(self.matrix[0])
        self.x = (BOARD_WIDTH - self.w) // 2
        self.y = 0

    def rotate(self):
        self.matrix = [list(row) for row in zip(*self.matrix[::-1])]
        self.h = len(self.matrix)
        self.w = len(self.matrix[0])

    def rotate_ccw(self):
        self.matrix = [list(row) for row in zip(*self.matrix)][::-1]
        self.h = len(self.matrix)
        self.w = len(self.matrix[0])


class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.board = [[0]*BOARD_WIDTH for _ in range(BOARD_HEIGHT)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.drop_delay = 1.0
        self.bag = []
        self.current = self.next_piece()
        self.next = self.next_piece()
        self.game_over = False
        self.paused = False
        self.last_drop = time.time()

    def next_piece(self):
        if not self.bag:
            self.bag = list(TETROMINOES.keys())
            random.shuffle(self.bag)
        shape = self.bag.pop()
        return Piece(shape)

    def valid(self, piece, nx=None, ny=None):
        x = piece.x if nx is None else nx
        y = piece.y if ny is None else ny
        for r in range(piece.h):
            for c in range(piece.w):
                if piece.matrix[r][c]:
                    bx = x + c
                    by = y + r
                    if bx < 0 or bx >= BOARD_WIDTH or by < 0 or by >= BOARD_HEIGHT:
                        return False
                    if self.board[by][bx]:
                        return False
        return True

    def lock_piece(self, piece):
        for r in range(piece.h):
            for c in range(piece.w):
                if piece.matrix[r][c]:
                    bx = piece.x + c
                    by = piece.y + r
                    if 0 <= by < BOARD_HEIGHT and 0 <= bx < BOARD_WIDTH:
                        self.board[by][bx] = piece.shape
        self.clear_lines()
        self.current = self.next
        self.next = self.next_piece()
        if not self.valid(self.current):
            self.game_over = True

    def clear_lines(self):
        new_board = [row for row in self.board if any(cell == 0 for cell in row)]
        cleared = BOARD_HEIGHT - len(new_board)
        if cleared:
            for _ in range(cleared):
                new_board.insert(0, [0]*BOARD_WIDTH)
            self.board = new_board
            self.lines += cleared
            self.score += (cleared * 100) * self.level
            self.level = 1 + self.lines // 10
            self.drop_delay = max(0.05, 1.0 - (self.level-1)*0.05)

    def hard_drop(self):
        while self.valid(self.current, ny=self.current.y+1):
            self.current.y += 1
            self.score += 2
        self.lock_piece(self.current)

    def step(self):
        if self.paused or self.game_over:
            return
        now = time.time()
        if now - self.last_drop >= self.drop_delay:
            if self.valid(self.current, ny=self.current.y+1):
                self.current.y += 1
            else:
                self.lock_piece(self.current)
            self.last_drop = now

    def rotate_current(self, ccw=False):
        old_matrix = [row[:] for row in self.current.matrix]
        old_w, old_h = self.current.w, self.current.h
        if ccw:
            self.current.rotate_ccw()
        else:
            self.current.rotate()
        for dx in (0, -1, 1, -2, 2):
            if self.valid(self.current, nx=self.current.x+dx):
                self.current.x += dx
                return
        self.current.matrix = old_matrix
        self.current.w, self.current.h = old_w, old_h

    def move_current(self, dx):
        if self.valid(self.current, nx=self.current.x+dx):
            self.current.x += dx

    def soft_drop(self):
        if self.valid(self.current, ny=self.current.y+1):
            self.current.y += 1
            self.score += 1
        else:
            self.lock_piece(self.current)

    def draw(self):
        s = self.stdscr
        s.clear()
        top = 1
        left = 2
        for r in range(BOARD_HEIGHT+2):
            s.addstr(top + r, left-2, '|')
            s.addstr(top + r, left + BOARD_WIDTH*2, '|')
        s.addstr(top+BOARD_HEIGHT+1, left-1, '-' * (BOARD_WIDTH*2+1))

        for r in range(BOARD_HEIGHT):
            for c in range(BOARD_WIDTH):
                cell = self.board[r][c]
                if cell:
                    color = COLORS.get(cell, 1)
                    try:
                        s.attron(curses.color_pair(color))
                        s.addstr(top + r, left + c*2, '[]')
                        s.attroff(curses.color_pair(color))
                    except curses.error:
                        s.addstr(top + r, left + c*2, '[]')
                else:
                    s.addstr(top + r, left + c*2, ' .')

        p = self.current
        for r in range(p.h):
            for c in range(p.w):
                if p.matrix[r][c]:
                    by = top + p.y + r
                    bx = left + (p.x + c)*2
                    if 0 <= by < top + BOARD_HEIGHT:
                        try:
                            s.attron(curses.color_pair(COLORS.get(p.shape,1)))
                            s.addstr(by, bx, '[]')
                            s.attroff(curses.color_pair(COLORS.get(p.shape,1)))
                        except curses.error:
                            s.addstr(by, bx, '[]')

        s.addstr(1, left + BOARD_WIDTH*2 + 4, 'Next:')
        np = self.next
        for r in range(np.h):
            for c in range(np.w):
                if np.matrix[r][c]:
                    try:
                        s.attron(curses.color_pair(COLORS.get(np.shape,1)))
                        s.addstr(2 + r, left + BOARD_WIDTH*2 + 4 + c*2, '[]')
                        s.attroff(curses.color_pair(COLORS.get(np.shape,1)))
                    except curses.error:
                        s.addstr(2 + r, left + BOARD_WIDTH*2 + 4 + c*2, '[]')

        s.addstr(8, left + BOARD_WIDTH*2 + 4, f'Score: {self.score}')
        s.addstr(9, left + BOARD_WIDTH*2 + 4, f'Lines: {self.lines}')
        s.addstr(10, left + BOARD_WIDTH*2 + 4, f'Level: {self.level}')
        if self.paused:
            s.addstr(12, left + BOARD_WIDTH*2 + 4, 'PAUSED')
        if self.game_over:
            s.addstr(14, left + BOARD_WIDTH*2 + 4, 'GAME OVER')
            s.addstr(15, left + BOARD_WIDTH*2 + 4, 'Press q to quit')
        s.refresh()


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    # Farben sicher initialisieren
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        try:
            curses.init_pair(1, curses.COLOR_MAGENTA, -1)
            curses.init_pair(2, curses.COLOR_YELLOW, -1)
            curses.init_pair(3, curses.COLOR_BLUE, -1)
            curses.init_pair(4, curses.COLOR_CYAN, -1)
            curses.init_pair(5, curses.COLOR_GREEN, -1)
            curses.init_pair(6, curses.COLOR_WHITE, -1)
            curses.init_pair(7, curses.COLOR_RED, -1)
        except curses.error:
            pass

    game = Game(stdscr)

    while True:
        try:
            if game.game_over:
                game.draw()
                ch = stdscr.getch()
                if ch in (ord('q'), ord('Q')):
                    break
                time.sleep(0.05)
                continue

            ch = stdscr.getch()
            if ch != -1:
                if ch in (curses.KEY_LEFT, ord('h')):
                    game.move_current(-1)
                elif ch in (curses.KEY_RIGHT, ord('l')):
                    game.move_current(1)
                elif ch in (curses.KEY_DOWN, ord('j')):
                    game.soft_drop()
                elif ch == ord(' '):
                    game.hard_drop()
                elif ch in (ord('z'), ord('Z')):
                    game.rotate_current(ccw=True)
                elif ch in (ord('x'), ord('X')):
                    game.rotate_current(ccw=False)
                elif ch in (ord('p'), ord('P')):
                    game.paused = not game.paused
                elif ch in (ord('q'), ord('Q')):
                    break

            game.step()
            game.draw()
            time.sleep(0.01)
        except KeyboardInterrupt:
            break


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except Exception as e:
        print('Fehler:', e)
        sys.exit(1)
