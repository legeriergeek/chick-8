import random
import pygame
import sys
import time

#Defining necessary variables
memory = [0] * 4096 # 4kb of memory
V = [0] * 16 # 16 8-bit registers
I = 0 #16 bit address register
pc = 0x200 # CP, starts at 0x200 because it's where the ROM is loaded
screen = [[0]*64 for _ in range(32)] #Stores screen pixel value
stack = []
keys = [False] * 16
delayTimer = 0

TIMER_FREQUENCY = 60
CPU_FREQUENCY = 500

def load_rom(filename):
    with open(filename, "rb") as f:
        rom = f.read()
    for i, byte in enumerate(rom):
        memory[0x200 + i] = byte

def fetch_instruction():
    return (memory[pc] << 8) | memory[pc + 1]

def execute_instruction(opcode):
    global pc, I
    match opcode & 0xF000:
        case 0x0000:
            match opcode:
                case 0x00E0:
                    clear_screen()
                    pc += 2
                case 0x00EE:
                    pc = stack.pop()
                case _:
                    pass
        case 0x1000:
            address = opcode & 0x0FFF
            jump(address)
        case 0x6000:
            x = (opcode & 0x0F00) >> 8
            nn = opcode & 0x00FF
            V[x] = nn
            pc += 2
        case 0x7000:
            x = (opcode & 0x0F00) >> 8
            nn = opcode & 0x00FF
            V[x] = (V[x] + nn) & 0xFF
            pc += 2
        case 0xA000:
            NNN = opcode & 0x0FFF
            I = NNN
            pc += 2
        case 0x2000:
            stack.append(pc + 2)
            address = opcode & 0x0FFF
            jump(address)
        case 0x3000:
            x = (opcode & 0x0F00) >> 8
            nn = opcode & 0x00FF
            if V[x] == nn:
                pc += 4
            else:
                pc += 2
        case 0x4000:
            x = (opcode & 0x0F00) >> 8
            nn = opcode & 0x00FF
            if V[x] != nn:
                pc += 4
            else:
                pc += 2
        case 0x5000:
            x = (opcode & 0x0F00) >> 8
            y = (opcode & 0x00F0) >> 4
            if V[x] == V[y]:
                pc += 4
            else:
                pc += 2
        case 0x9000:
            x = (opcode & 0x0F00) >> 8
            y = (opcode & 0x00F0) >> 4
            if V[x] != V[y]:
                pc += 4
            else:
                pc += 2
        case 0x8000:
            x = (opcode & 0x0F00) >> 8
            y = (opcode & 0x00F0) >> 4
            subcode = opcode & 0x000F
            match subcode:
                case 0x0:
                    V[x] = V[y]
                case 0x1:
                    V[x] |= V[y]
                case 0x2:
                    V[x] &= V[y]
                case 0x3:
                    V[x] ^= V[y]
                case 0x4:
                    total = V[x] + V[y]
                    V[0xF] = 1 if total > 0xFF else 0
                    V[x] = total & 0xFF    
                case 0x5:
                    V[0xF] = 1 if V[x] > V[y] else 0
                    V[x] = (V[x] - V[y]) & 0xFF
                case 0xE:
                    V[0xF] = (V[x] >> 7) & 1  
                    V[x] = (V[x] << 1) & 0xFF 
                case 0x6:
                    V[0xF] = V[x] & 0x1  # bit 0 (le dernier à droite)
                    V[x] >>= 1
                case _:
                    print(f"unknown subcode '0x8000' 0x{subcode:01X}")                     
            pc += 2
        case 0xC000:
            x = (opcode & 0x0F00) >> 8
            nn = opcode & 0x00FF
            randNum = random.randint(0,255)
            V[x] = randNum & nn
            pc += 2
        case 0xD000:
            x = V[(opcode & 0x0F00) >> 8]
            y = V[(opcode & 0x00F0) >> 4]
            height = opcode & 0x000F            
            V[0xF] = 0
            for row in range(height):
                sprite_byte = memory[I + row]
                for col in range(8):
                    sprite_pixel = (sprite_byte >> (7 - col)) & 1
                    screen_x = (x + col) % 64
                    screen_y = (y + row) % 32
                    if screen[screen_y][screen_x] == 1 and sprite_pixel == 1:
                        V[0xF] = 1
                    screen[screen_y][screen_x] ^= sprite_pixel
            pc += 2
        case 0xF000:
            global delayTimer
            x = (opcode & 0x0F00) >> 8
            nn = opcode & 0x00FF
            match nn:
                case 0x1E:
                    I = (I + V[x]) & 0xFFFF 
                    pc += 2
                case 0x65:
                    for i in range (x + 1):
                        V[i] = memory[I+i]
                    pc += 2
                case 0x55:
                    for i in range (x+1):
                        memory[I + i] = V[i]
                    pc += 2
                case 0x0A:
                    keyPressed = False
                    for i in range(16):
                        if keys[i]:
                            V[x] = i
                            keyPressed = True
                            #print("key pressed!")
                            break
                    if not keyPressed:
                        #print("key aint pressed")
                        return
                    pc += 2
                #idgaf abt sound
                case 0x18:
                    pc += 2
                case 0x29:
                    I = 0x50 + (V[x] * 5)
                    pc += 2
                case 0x15:
                    delayTimer = V[x]
                    pc += 2
                case 0x07:
                    V[x] = delayTimer
                    pc += 2
                case 0x33:
                    value = V[x]
                    memory[I] = value // 100
                    memory[I + 1] = (value // 10) % 10
                    memory[I + 2] = value % 10
                    pc += 2
                case _:
                    print(f"unknown subcode '0xF000' 0x{nn:02X}")
        
        case 0xE000:
            x = (opcode & 0x0F00) >> 8
            keyChecked = V[x]
            subcode = opcode & 0x00FF
            match subcode:
                case 0x9E:
                    if not keys[keyChecked]:
                        pc += 2
                    else:
                        pc += 4
                case 0xA1:
                    if keys[keyChecked]:
                        pc += 2
                    else:
                        pc += 4
                case _:
                    print(f"'OxEOOO' subcode named 0x{subcode:02X} is unknown")
        case 0xB000:
            NNN = opcode & 0x0FFF
            jump(NNN + V[0]) 
        case _:
            print(f"could not find opcode{opcode:04X}")
        




def clear_screen():
    for y in range(32):
        for x in range(64):
            screen[y][x] = 0

def jump(address):
    global pc
    pc = address

def initPygame():
    global pyScreen
    global white
    global clock
    pygame.init()
    pyScreen = pygame.display.set_mode((640, 320))
    pygame.display.set_caption("CHIP-8 Emulator")
    white = (255,255,255)
    pyScreen.fill("black")
    clock = pygame.time.Clock()
    pygame.display.flip()

def drawScreen(screen):
    pyScreen.fill("black")
    for y in range(32):
        for x in range(64):
            if screen[y][x] == 1:
                rect = pygame.Rect(x * 10, y * 10, 10, 10)
                pygame.draw.rect(pyScreen, white, rect)
    pygame.display.flip()
    #pygame.time.delay(10)  # the chpeed

def updateTimer():
    global delayTimer
    if delayTimer > 0:
        delayTimer -= 1

def handleInput():
    # mapped for azerty, sorry!
    keymap = {
        pygame.K_x: 0,
        pygame.K_1: 1,
        pygame.K_2: 2, 
        pygame.K_3: 3,
        pygame.K_a: 4,
        pygame.K_z: 5, 
        pygame.K_e: 6,
        pygame.K_q: 7,
        pygame.K_s: 8,
        pygame.K_d: 9,
        pygame.K_w: 10, #A
        pygame.K_c: 11, #B
        pygame.K_4: 12, #C
        pygame.K_r: 13, #D
        pygame.K_f: 14, #E
        pygame.K_v: 15  #F
    }

    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key in keymap:
                keys[keymap[event.key]] = True
        elif event.type == pygame.KEYUP:
            if event.key in keymap:
                keys[keymap[event.key]] = False
        


if len(sys.argv) < 2:
    print("Usage: chick8 rom.ch8")
    sys.exit(1)

rom_path = sys.argv[1]

load_rom(rom_path)

fontset = [
    0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
    0x20, 0x60, 0x20, 0x20, 0x70,  # 1
    0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
    0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
    0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
    0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
    0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
    0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
    0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
    0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
    0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
    0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
    0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
    0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
    0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
    0xF0, 0x80, 0xF0, 0x80, 0x80   # F
]

# Charger le fontset en mémoire (généralement à l'adresse 0x50)
for i, byte in enumerate(fontset):
    memory[0x50 + i] = byte

instructions_per_frame = CPU_FREQUENCY // TIMER_FREQUENCY 

print("\"CHICK-8\" CHIP-8 Emulator --- Made by legeriergeek")
print("Memory: 4Kb\nDisplay: pygame\nClockspeed: 500Hz (Instructions per Second)")
print("Press ^C to quit.")

initPygame()

while True:
    for _ in range(instructions_per_frame):
        opcode = fetch_instruction()
        execute_instruction(opcode)

    drawScreen(screen)
    handleInput()
    updateTimer()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    clock.tick(TIMER_FREQUENCY)


