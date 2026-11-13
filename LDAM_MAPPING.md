# LDAM Mapping: Logic Design & Microprocessor Architecture

## 1. Project Context & Academic Objective

This document bridges the **Phase 1 Software Foundation** of the `BarcodeReader` system to the core academic principles of **Logic Design and Microprocessor (LDAM)**.

The software foundation implements the business logic, data models, validation checks, and interactive user interfaces using Python, FastAPI, and modern web standards. In subsequent phases, this logic will be mapped into embedded C / Assembly and executed on a target microcontroller unit (MCU) interfaced with a physical barcode scanner, character LCD, status LEDs, and a buzzer.

---

## 2. End-to-End System Flow

The system processes barcodes through a unidirectional pipeline:

```
+------------------------+
| Physical Barcode       |
| Scanner (Optical / CCD)|
+-----------+------------+
            |
            | Raw Photodiode Signal / Decoded ASCII
            v
+------------------------+
| Input Communication    |  <-- UART Serial (TTL / RS-232) or USB HID Keyboard Wedge
| Interface (Transceiver)|
+-----------+------------+
            |
            | Character Stream (e.g., 'B', 'R', '0', '0', '0', '0', '0', '1', '\r')
            v
+------------------------+
| Input Buffer & FSM     |  <-- Ring / Circular Buffer in MCU SRAM
| (Controller Core)      |
+-----------+------------+
            |
            | Complete Frame Delimited by CR/LF
            v
+------------------------+
| Format & Integrity     |  <-- Length check, ASCII range check, checksum verification
| Validation             |
+-----------+------------+
            |
            | Validated Barcode Key
            v
+------------------------+
| Lookup Table Engine    |  <-- Flash / ROM / EEPROM Record Matching & Category Pointer
| (Memory Hierarchy)     |
+-----------+------------+
            |
      +-----+-----+
      |           |
[Match Found]  [Not Found / Malformed]
      |           |
      v           v
+------------------------------------+
| Output Actuation & Display         |  <-- 16x2 HD44780 LCD, Green/Red GPIO LEDs, Buzzer
+------------------------------------+
```

---

## 3. Implementation Status: Software Phase 1 vs. Hardware Future

To maintain strict academic integrity, the following matrix differentiates the implemented Phase 1 software architecture from the planned hardware implementation.

| Subsystem Component | Software Prototype (Phase 1 & Phase 2) | Future Hardware Integration (Planned) |
| :--- | :--- | :--- |
| **Barcode Input Channel** | Multi-mode: USB keyboard-wedge emulation, Static Image Upload, & Live Mobile Camera Scanning (ZXing) | Hardware laser/CCD barcode reader module (e.g. GM65) or CMOS image sensor (OV7670) |
| **Input Communication** | HTTP REST `POST /api/scan` JSON payload | Hardware UART (Rx/Tx) or USB Host Controller IC (MAX3421E) |
| **Input Buffering** | Pydantic model validation & browser client memory buffer | Fixed-size Circular FIFO Buffer in MCU SRAM (Interrupt-driven) |
| **Image Preprocessing** | Client-side HTML5 Canvas pixel downscaling & HybridBinarizer | Dedicated hardware ASIC decoder or DMA-driven frame buffer with Otsu binarizer |
| **State Machine (FSM)** | Asynchronous event loop & client-side UI state tracking | Finite State Machine implemented in C/Assembly switch-case |
| **Data Storage** | Normalized JSON files (`categories.json`, `products.json`) | Read-Only Flash ROM lookup tables (`PROGMEM`) or external EEPROM |
| **Category Resolution** | Dynamic relational lookup via Python dictionary indexing | Pointer indirection / array index referencing category string table |
| **Primary Output** | HTML5 / CSS3 responsive web card with category badge | 16x2 / 20x4 Alphanumeric LCD (HD44780) via 4-bit parallel bus / I2C |
| **Status Indicators** | UI alert banners (green success, red error, amber warning) | Active-HIGH GPIO lines driving discrete Red/Green LEDs |
| **Audio Feedback** | Visual indicators & session history logging | Piezoelectric buzzer driven by PWM / Timer pin for frequency tones |

---

## 4. LDAM Technical Concepts & Hardware Realization

### 4.1. Serial Communication via UART

In the hardware phase, the barcode scanner communicates with the microcontroller over a universal asynchronous receiver-transmitter (UART) interface.

1. **Physical & Electrical Layer:**
   - **Signal Levels:** TTL logic levels (0V = Logic Low, 3.3V/5V = Logic High). If the scanner uses RS-232 voltage levels (-12V to +12V), a level transceiver (such as MAX232 or MAX3232) is placed between the scanner and MCU RX pin.
   - **Baud Rate:** Configured to match scanner output, typically `9600 bps` or `115200 bps`.
   - **Frame Format (8-N-1):**
     - 1 Start Bit (Logic 0 / Space)
     - 8 Data Bits (LSB first, ASCII character payload)
     - No Parity Bit (Parity disabled)
     - 1 Stop Bit (Logic 1 / Mark)

2. **Microcontroller Peripheral Configuration:**
   - **Baud Rate Generator:** Derived from MCU system clock using the timer or dedicated baud rate register:
     $$\text{UBRR} = \frac{f_{\text{osc}}}{16 \times \text{Baud Rate}} - 1$$
   - **Interrupt Service Routine (ISR):**
     Instead of busy-waiting (polling the UART Data Register `RXC` flag), an **Interrupt-Driven RX Architecture** is used. When a byte arrives, the UART hardware fires a `USART_RX_vect` interrupt, which deposits the received byte into the ring buffer without halting main CPU instruction execution.

---

### 4.2. Input Buffering & FIFO Management

A barcode scanner transmits a sequence of ASCII characters at high speeds (e.g., 8 to 16 characters in rapid succession) followed by a carriage return (`\r`, ASCII `0x0D`) or line feed (`\n`, ASCII `0x0A`).

1. **Circular Ring Buffer in SRAM:**
   - Pre-allocated array: `uint8_t rx_buffer[32];`
   - Two memory pointers / indices:
     - `volatile uint8_t head`: points to the next available write slot (incremented by ISR).
     - `volatile uint8_t tail`: points to the next byte to be read by the main processing loop.
2. **Buffer Guard & Overflow Protection:**
   - Before writing to `head`, the ISR checks: `((head + 1) % BUFFER_SIZE) != tail`.
   - If full, a buffer overflow flag is set and further characters are dropped to prevent memory corruption.
3. **Frame Delimiter Detection:**
   - When the ISR receives `0x0D` (`\r`), it asserts a `frame_ready` flag, alerting the Finite State Machine that a complete barcode is ready for parsing.

---

### 4.3. Finite State Machine (FSM) Design

The controller logic operates as a deterministic **Moore/Mealy Finite State Machine**:

```
                  +-------------------------+
                  |         S0_IDLE         |<-----------------------------+
                  | Green=0, Red=0, LCD="Scan"|                             |
                  +------------+------------+                             |
                               | Start byte received                      |
                               v                                          |
                  +-------------------------+                             |
                  |     S1_ACCUMULATING     |                             |
                  | Store char in ring buf  |                             |
                  +------------+------------+                             |
                               | Frame Delimiter ('\r')                   |
                               v                                          |
                  +-------------------------+                             |
                  |       S2_VALIDATE       |                             |
                  | Check length & prefix   |                             |
                  +-----+-------------+-----+                             |
                        |             |                                   |
         Invalid format |             | Valid format                      |
                        v             v                                   |
           +---------------+   +----------------+                         |
           |   S5_ERROR    |   |   S3_LOOKUP    |                         |
           | Red=1, Beep x2|   | Search Flash   |                         |
           +-------+-------+   +---+--------+---+                         |
                   |               |        |                             |
                   |   Match Found |        | Not Found                   |
                   |               v        v                             |
                   |       +---------------+  |                           |
                   |       |   S4_MATCH    |  |                           |
                   |       |Green=1,Beep x1|  |                           |
                   |       +-------+-------+  |                           |
                   |               |          |                           |
                   +-------+-------+----------+                           |
                           |                                              |
                           v                                              |
                  +-------------------------+                             |
                  |     S6_DISPLAY_HOLD     |                             |
                  | Hold display 3 seconds  |                             |
                  +------------+------------+                             |
                               | Timeout elapsed                          |
                               +------------------------------------------+
```

#### FSM State Descriptions:
1. **`S0_IDLE`:** Microcontroller is listening. Status LEDs are OFF or pulsating. LCD displays `"Ready to Scan"`.
2. **`S1_ACCUMULATING`:** UART bytes are actively arriving and being appended to the input buffer. Watchdog timer armed.
3. **`S2_VALIDATE`:** Delimiter detected. Validates that the payload is non-empty, contains valid alphanumeric characters, and matches expected length bounds (e.g., 8 bytes for `BR000001`).
4. **`S3_LOOKUP`:** Executes table lookup against pre-compiled catalogue stored in non-volatile memory.
5. **`S4_MATCH`:** Product identified. Triggers Category resolution, sets Green LED HIGH, sounds a 1 kHz 100 ms confirmation beep, writes product and category name to LCD.
6. **`S5_ERROR`:** Barcode unrecognized or malformed. Sets Red LED HIGH, sounds a 250 Hz double beep, displays `"UNKNOWN BARCODE"` on LCD.
7. **`S6_DISPLAY_HOLD`:** Keeps output stable for inspection (e.g., 3 seconds) using a hardware timer, clears buffer pointers, and resets to `S0_IDLE`.

---

### 4.4. Lookup Table & Memory Organization

In standard microprocessors (e.g., 8051, PIC, AVR ATmega328P, ARM Cortex-M), internal SRAM is severely constrained (often 2 KB to 8 KB), while Flash ROM is larger (32 KB to 256 KB).

1. **Storage in Program Memory (Flash / PROGMEM):**
   Product catalogues are stored as read-only constants in Program Flash rather than loaded into volatile RAM.

2. **Embedded Record Structure (in C):**
   ```c
   typedef struct {
       uint8_t category_id;
       char name[24];
   } CategoryRecord;

   typedef struct {
       char barcode[9];     // Fixed 8 chars + null terminator
       uint8_t category_id; // Foreign key referencing category table
       char name[32];       // Product display name
   } ProductRecord;

   // Category Table stored in Flash Memory
   const CategoryRecord CATEGORY_TABLE[8] PROGMEM = {
       {1, "Dress - Casual"},
       {2, "Dress - Party Wear"},
       {3, "Kurti - Cotton"},
       {4, "Cat 4 - Pending"},
       {5, "Abaya"},
       {6, "Rental - Bridal"},
       {7, "Dress - Material"},
       {8, "Dress - Ready Wear"}
   };

   // Product Table stored in Flash Memory (Ordered for binary search)
   const ProductRecord PRODUCT_TABLE[16] PROGMEM = {
       {"BR000001", 1, "Floral Summer Maxi Dress"},
       {"BR000002", 1, "Linen A-Line Day Dress"},
       {"BR000003", 2, "Sequin Evening Cocktail Gown"},
       // ... additional records
   };
   ```

3. **Lookup Complexity & Search Algorithm:**
   - **Linear Scan:** $\mathcal{O}(N)$ memory comparisons (`strcmp_P`). Acceptable for small demo catalogues ($N \le 32$).
   - **Binary Search:** $\mathcal{O}(\log_2 N)$ comparisons. Ideal for Flash arrays pre-sorted by barcode string.
   - **Direct Hash Indexing:** $\mathcal{O}(1)$ numeric table lookup if barcodes are numerically contiguous.

---

### 4.5. LCD / Display Output Subsystem

The visual display presents the scanned product name and resolved category name.

1. **Display Hardware Interface:**
   - Standard **16x2 Alphanumeric LCD** powered by the **Hitachi HD44780** controller or equivalent.
   - **Bus Topology:**
     - **8-bit Parallel Mode:** 8 data lines ($D_0-D_7$) + 3 control lines ($RS, R/W, E$) = 11 MCU pins.
     - **4-bit Nibble Mode (Preferred):** 4 data lines ($D_4-D_7$) + 2 control lines ($RS, E$) = 6 MCU pins.
     - **I2C Serial Bus (PC8574 Backpack):** 2 MCU pins ($SDA, SCL$) utilizing the hardware Two-Wire Interface (TWI).

2. **Display Screen Mapping:**
   ```
   +--------------------------------+
   | Line 1: [Product Name (16c)]   |  --> "Floral Maxi D..."
   | Line 2: [Category Name (16c)]  |  --> "Dress - Casual  "
   +--------------------------------+
   ```

3. **Software Control Flow:**
   - Initialize controller (Function Set, Display ON/OFF control, Entry Mode).
   - Clear display instruction (`0x01`).
   - Write ASCII bytes sequentially to LCD Data Register (`DR`).

---

### 4.6. GPIO-Based Status Indicators & Audio Actuation

1. **Visual Output Pins:**
   - **Port Configuration:** Data Direction Registers (e.g. `DDRB`, `DDRD` or GPIO `MODER`) configure chosen pins as output.
   - **Green LED (Pin P1.0):** Driven HIGH via bit-set instruction (`PORTB |= (1 << PB0)`) when a valid barcode lookup succeeds.
   - **Red LED (Pin P1.1):** Driven HIGH when an unknown barcode or validation fault occurs.

2. **Acoustic Feedback (Piezo Buzzer):**
   - Connected to a Timer Output Compare pin (e.g., `OC1A`).
   - Configured in **CTC Mode (Clear Timer on Compare Match)** or PWM mode to produce audible frequencies:
     - **Success Tone:** Single high-frequency pulse (1.2 kHz, 80 ms duration).
     - **Error Tone:** Double low-frequency buzz (300 Hz, 150 ms pulse, 100 ms gap, 150 ms pulse).

---

### 4.7. Error & Exception Handling Architecture

The system implements multi-tiered validation:

1. **Framing & Framing Errors:** If the stop bit is not received when expected, a UART Framing Error (`FE`) is registered, aborting the read.
2. **Buffer Overrun:** If incoming characters exceed buffer capacity before a newline is detected, the buffer is flushed and an error state is asserted.
3. **Empty / Null Input:** Submitting empty carriage returns does not trigger table lookups.
4. **Key Miss (Not Found):** If the barcode does not exist in `PRODUCT_TABLE`, the MCU signals `S5_ERROR` without crashing or entering an undefined state.
5. **Watchdog Timer (WDT):** Ensures that if the controller hangs in an unexpected loop during serial reception, a hardware reset occurs after a configured prescaler period (e.g., 2 seconds).

---

### 4.8. 2D Optical Image Decoding vs. 1D Photodiode Scanners: Microprocessor RAM & Processing Constraints

In Phase 2, the system introduced 2D image-based barcode scanning (decoding images containing Code 128, EAN, and 2D codes). When translating this to embedded microprocessor systems, significant hardware architecture tradeoffs emerge:

1. **1D Photodiode / Laser Scanner Architecture:**
   - Detects light transitions as a single-dimensional analog waveform (black bars absorb laser light, white spaces reflect).
   - A hardware comparator converts the signal into a digital pulse train.
   - Microcontroller measures pulse widths using Timer Input Capture (`ICP1` pin).
   - **RAM Footprint:** Minimal (< 64 bytes for pulse-width transition arrays). Can run on ultra-low-cost 8-bit MCUs (e.g. ATmega328P, 8051).

2. **2D CMOS Image Sensor (Camera Module) Architecture:**
   - Captures full 2D pixel matrices (e.g. 640×480 grayscale = 307,200 bytes per frame).
   - Requires substantial SRAM frame buffers:
     - 8-bit microcontrollers (typically 2 KB SRAM) cannot hold uncompressed pixel arrays in memory.
     - 32-bit microcontrollers (e.g., STM32F4/F7 with Direct Memory Access (DMA) or ESP32 with external PSRAM) are required to buffer full image frames.
   - Image binarization (Otsu's thresholding or HybridBinarizer) requires significant arithmetic throughput, favoring hardware Floating Point Units (FPU) or DSP instructions.

3. **Smart Embedded Scanner Modules (The Hybrid Approach):**
   - In practical LDAM laboratory implementations, an integrated optical engine (such as the GM65 or Newland EM3080 module) contains its own internal CMOS sensor, DSP, and decoding firmware.
   - The module processes the 2D image internally and transmits the decoded barcode string via standard UART serial communication to the main project microcontroller.
   - This preserves the clean separation of concerns: the main microcontroller focuses on FSM sequencing, catalogue memory lookups, LCD actuation, and GPIO status signaling.

---

## 5. Summary of Deliverables

- **Phase 1 Deliverables:** Structured JSON catalogues, deterministic Python lookup engine, FastAPI REST backend, USB keyboard-wedge terminal interface, and 23 automated tests.
- **Phase 2 Deliverables:** Client-side image upload and preview, offline vendored ZXing decoding engine, multi-barcode detection with interactive selection, sample test images, and 8 image decoding integration tests (31 tests total).

