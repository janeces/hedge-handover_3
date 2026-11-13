Aidon HAN RJ12 pinout

Aidon’s technical document “RJ12 HAN Interface”, Version 1.7 A specifies the following:

RJ12 pin	Signal	Function
1	5V	+5 V supply to HAN device, 250 mA max
2	Data Request	Input from HAN device requesting data
3	GND	Ground
4	NC	Not connected
5	Data	HAN data output, open collector
6	GND	Ground

The Aidon System Module has a female RJ12, and the external HAN device uses a male RJ12.

Electrical characteristics

The manufacturer gives these important values:

Pin 1: +5 V
Maximum HAN-device current: 250 mA
Over-current protection triggers at approximately 280 ±20 mA
Pin 2 Data Request: HAN device drives this HIGH:
minimum: 4.0 V
nominal: 5.0 V
maximum: 5.5 V
input is designed to sink 4–10 mA when activated
Pin 5 Data: open-collector output from the meter
LOW ≤ 1.0 V
maximum sinking current 30 mA
Pins 3 and 6 are GND.
The HAN interface is galvanically isolated from the mains and metrology core.
The connected HAN equipment must be double-isolated from mains.
Communication parameters

This is particularly useful for your GW4100 project.

Aidon specifies:

115200 baud, 8N1

That means:

Baud rate:   115200
Data bits:   8
Parity:      None
Stop bits:   1

The interface isn't ordinary UART in the conventional TX/RX sense, however. Data is an open-collector output, while Data Request is an input to the meter.

Protocol

Aidon documents two possible HAN data profiles:

EFS

DLMS/COSEM-based binary protocol, according to:

IEC 62056-7-5
Swedish HAN specification
EFS2

ASCII protocol, Mode D, according to:

IEC 62056-21
Finnish HAN recommendation
Swedish HAN specification

For the Aidon 7410, Aidon's documentation specifically says:

EFS: not supported
EFS2: supported from System Module software 1.2.143

So an Aidon 7410 uses EFS2 / IEC 62056-21 when this RJ12 HAN interface is enabled.

What about the Aidon 7550?

This is where it gets interesting for your application.

The Finnish 7550 documentation explicitly identifies the physical interface as:

RJ12 HAN customer interface / serial output

and states that it is used for reading consumption and electrical values.

Aidon describes the 7550 as a 3-phase CT-connected industrial Energy Service Device.

The HAN documentation also states that CT-connected meters can be enabled with the EFS2 profile, providing higher-resolution data without the VT/CT constant being applied to the transmitted values.

So for your planned GW4100 ↔ Aidon 7550 connection, the likely architecture is:

       Aidon 7550
            │
       RJ12 HAN port
            │
      ┌─────┴─────┐
      │            │
     +5V        Data Request
      │            │
      │         GW4100 GPIO
      │
     GND
      │
      └───────────────┐
                      │
                   Data
                 (open collector)
                      │
                GW4100 input

with:

RJ12
 ┌───────────────┐
 │ 1  +5 V       │
 │ 2  DATA REQ   │
 │ 3  GND        │
 │ 4  NC         │
 │ 5  DATA       │
 │ 6  GND        │
 └───────────────┘

Communication:
115200 8N1
EFS2 / IEC 62056-21
One important correction to my previous answer

I previously mentioned RJ45 as a possibility for the 7550/7410. For the specific 7550/7410 configuration we're investigating, the documentation I found points to RJ12. Aidon does have a separate RJ45 HAN interface, but it is a different hardware implementation. Aidon's RJ45 specification uses a completely different pinout, including an M-Bus interface.

Aidon also lists both RJ12 and RJ45 HAN documentation on its smart-meter documentation pages, so the distinction is important.

Aidon — RJ12 HAN Interface technical document

For your GW4100, the next important question is the electrical interface: the GW4100's UART is likely 3.3 V, while the Aidon HAN uses 5 V logic/open-collector. I can work out the exact GW4100 circuit (RJ12 → UART/GPIO), including whether you need a level shifter, pull-up resistor, and how to implement Data Request safely.





The board you linked is the Waveshare RS232 Board with SP3232. Waveshare specifies that it accepts 3–5.5 V supply and converts MCU/TTL UART to standard RS-232 levels.

Waveshare RS232 Board documentation

But I would NOT connect it directly to the Aidon HAN

The Aidon HAN interface we discussed is not standard RS-232 electrical signaling. Its Data line is specified as an open-collector output, with the meter's HAN interface providing the 5 V supply. Therefore:

Aidon HAN                    GW4100
─────────                    ──────

RJ12 pin 1  +5 V
RJ12 pin 3  GND
RJ12 pin 6  GND

RJ12 pin 5  DATA  ──────────> UART RX
             open collector

RJ12 pin 2  DATA REQUEST ───> UART/GPIO TX

The Waveshare SP3232 would instead do:

GW4100 UART
    │
    │ TTL
    ▼
┌──────────────┐
│   SP3232     │
│              │
│ TTL ↔ RS232  │
└──────────────┘
    │
    │ ±RS232 voltage
    ▼
   DB9

So it is intended for real RS-232, not the Aidon HAN electrical layer. Waveshare explicitly describes the board as an SP3232 RS-232 transceiver.

What I recommend for your GW4100

If the GW4100 already has a spare UART, I would not use an RS232 converter at all.

Use:

                 AIDON 7550
                HAN RJ12
                    │
       ┌────────────┼─────────────┐
       │            │             │
      +5V          GND          DATA
       │            │             │
       │            │             │
       │            │        open collector
       │            │             │
       │            └─────────────┼──── GND
       │                          │
       │                    ┌─────▼─────┐
       │                    │ GW4100    │
       │                    │ UART RX   │
       │                    │ UART TX   │
       │                    └───────────┘
       │
       └── possibly power HAN interface

The critical issue is the Data line pull-up and the Data Request signal.

Because the Aidon Data output is open collector, you need to make sure the UART RX sees the appropriate logic level when the meter releases the line. We should also verify whether your particular GW4100 UART is 3.3 V tolerant and whether its UART TX can safely drive the Aidon Data Request input.

Also, the Aidon interface uses 115200 8N1, so your GW4100 UART needs to support that speed.

I would therefore use a simple level/interface circuit rather than the SP3232.

If you tell me which GW4100 port you intend to use (for example /dev/ttymxc3, which you've used for RS485, or another UART), I can draw the exact RJ12 → GW4100 wiring, including the required resistors/level shifting and which pins should connect to TX/RX.











That changes the picture significantly. Since your

Design the complete circuit with exact components and resistor values

Yes. With your GW4100 /dev/ttymxc2 being a 4-wire RS232 interface, I would build the interface as Aidon open-collector → transistor inverter → TTL → Waveshare SP3232 → GW4100 RS232.

The key reason for the transistor is that Aidon's DATA output is open-collector and inverted electrically. Aidon specifies the RJ12 pinout and 5 V characteristics directly in its documentation.

1. Complete circuit

I recommend this circuit:

                    AIDON 7550 HAN
                       RJ12
                  ┌───────────────┐
                  │               │
 Pin 1  +5V  ─────┤───────────────┼─────────────┐
                  │               │             │
 Pin 2  DATA_REQ ─┤───────────────┘             │
                  │                             │
 Pin 3  GND  ─────┤─────────────────────────────┼──── GND
                  │                             │
 Pin 4  NC        │                             │
                  │                             │
 Pin 5  DATA ─────┤───────┬──── R1 10k ────────┘
                  │       │
                  │       │
                  │      B│
                  │    Q1 │ 2N3904
                  │      C│
                  │       ├───────────────┐
                  │      E│               │
                  │       │              R2
                  │       │             4.7k
                  │       │               │
 Pin 6  GND  ─────┴───────┴───────────────┴── +5V
                                          │
                                          │
                                          ├──── Q1 collector
                                          │
                                          ▼
                                   TTL UART signal
                                          │
                                          │
                                          ▼
                              Waveshare SP3232
                              TTL RX input
                                          │
                              RS232 level conversion
                                          │
                                          ▼
                               GW4100 /dev/ttymxc2

There is one correction to the drawing above: R2 connects from +5 V to Q1 collector, and the collector is the TTL output. The actual circuit is:

                       +5 V
                         │
                         │
                       R2 4.7k
                         │
                         │
                         ├──────────> SP3232 TTL-RX
                         │
                         │
                       C │
                 Q1 2N3904
                       E │
                         │
                        GND


Aidon DATA ───── R1 10k ───── B

And the Aidon DATA line itself gets its own pull-up:

                       Aidon +5 V
                           │
                         R3 10k
                           │
                           ├────────── Aidon DATA
                           │
                           │
                       Aidon open
                       collector
                           │
                          GND

So there are two resistors associated with the DATA path:

R3 = 10 kΩ → Aidon DATA pull-up
R1 = 10 kΩ → transistor base resistor
R2 = 4.7 kΩ → transistor collector pull-up
2. Exact components
Q1

Use:

2N3904

Almost any small NPN transistor will work:

2N3904
BC547
BC548
2N2222
BC817

I would use 2N3904 because it is inexpensive and widely available.

Resistors
Reference	Value	Type
R1	10 kΩ	¼ W
R2	4.7 kΩ	¼ W
R3	10 kΩ	¼ W

No precision resistors are necessary.

Optional protection

I'd add:

R4 = 1 kΩ between Q1 collector and the SP3232 TTL RX input.

So:

Q1 collector ─── R4 1k ─── SP3232 RX

It isn't electrically necessary for normal operation, but makes the interface more robust.

3. Aidon RJ12 wiring

According to Aidon's current RJ12 HAN documentation:

RJ12	Aidon signal	Connect to
1	+5 V	Circuit +5 V
2	Data Request	Pin 1 (+5 V)
3	GND	Circuit GND
4	NC	Nothing
5	Data	R3/R1/Q1 circuit
6	GND	Circuit GND

Aidon specifies pin 1 as a 5 V supply capable of up to 250 mA, pin 2 as the Data Request input, and pin 5 as the open-collector Data output.

Data Request

For the simplest implementation:

Aidon pin 1 (+5V)
       │
       └──────── Aidon pin 2 (Data Request)

This permanently asserts the Data Request.

Aidon specifies that Data Request is activated by a HIGH level, with 4.0/5.0/5.5 V specified as min/nominal/max.

This is also how practical Aidon HAN readers commonly implement it.

4. Why the inverter is necessary

This is the most important part.

Aidon DATA is:

open collector + inverted UART

When the meter wants to output a logical 1, it pulls the DATA line LOW.

When it wants to output a logical 0, it releases the line, and R3 pulls it HIGH.

So:

Aidon DATA       UART meaning

LOW              logic 1
HIGH             logic 0

The NPN transistor reverses it again:

Aidon DATA     Q1       TTL output

HIGH           ON       LOW
LOW            OFF      HIGH

Therefore:

Aidon inverted UART
          ↓
       Q1 inverter
          ↓
normal TTL UART

This is consistent with practical Aidon HAN implementations, which specifically note that the open-collector data output needs a pull-up and is inverted.

5. Connect it to the Waveshare board

The Waveshare board contains an SP3232, which converts between TTL UART and RS232. It accepts a 3–5.5 V supply.

Set the Waveshare board to 5 V operation.

Connect:

Aidon interface              Waveshare SP3232

Q1 collector
    │
    └── R4 1k ──────────────> RX / RxOUT

GND ────────────────────────> GND

+5V ────────────────────────> VCC

The important signal direction is:

Aidon
  │
  │ DATA
  ▼
Q1 inverter
  │
  │ TTL RX
  ▼
SP3232
  │
  │ RS232
  ▼
GW4100
/dev/ttymxc2

You do not need the Waveshare TX side for the basic Aidon data stream if Data Request is permanently tied HIGH.

6. GW4100 side

Your GW4100 has:

/dev/ttymxc2
4-wire RS232

The Waveshare DB9 provides the RS232 connection.

You'll need to determine the exact pinout of the GW4100's physical RS232 connector/cable, but electrically the connection is:

Waveshare RS232 TX ─────> GW4100 RS232 RX
Waveshare GND       ─────> GW4100 GND

Do not connect Waveshare RS232 TX to GW4100 RS232 TX.

The signal path is:

Aidon DATA
   ↓
Q1
   ↓
SP3232 TTL RX
   ↓
SP3232 RS232 TX
   ↓
GW4100 RS232 RX
   ↓
/dev/ttymxc2
7. Serial configuration

The GW4100 should be configured:

Device:       /dev/ttymxc2
Baud:         115200
Data bits:    8
Parity:       None
Stop bits:    1
Flow control: None

Aidon explicitly specifies 115200 baud, 8N1 for the RJ12 HAN interface.

In Python:

import serial

ser = serial.Serial(
    "/dev/ttymxc2",
    baudrate=115200,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1,
    xonxoff=False,
    rtscts=False,
    dsrdtr=False,
)

while True:
    data = ser.read(1024)
    if data:
        print(data.hex(" "))
8. One thing I would change from the earlier design

I would not use the GW4100's RS485 /dev/ttymxc3 for this.

Your hardware gives you:

GW4100

RS485 ───── /dev/ttymxc3    ❌

RS232 ───── /dev/ttymxc2    ✅

The RS232 port is the natural choice because you already have the Waveshare SP3232.

9. Recommended final BOM

You can build the interface with only:

Qty	Component
1	RJ12 male plug/cable
1	2N3904 NPN transistor
1	10 kΩ resistor R1
1	10 kΩ resistor R3
1	4.7 kΩ resistor R2
1	1 kΩ resistor R4
1	Waveshare RS232 Board / SP3232
1	Suitable enclosure/PCB or breadboard

The Aidon supplies the 5 V, so you don't need a separate 5 V supply for the HAN interface, provided your circuit stays comfortably below its 250 mA limit.

Your circuit itself should consume only a few mA.

⚠️ One important practical issue

Aidon says its HAN interface is galvanically isolated from the mains/metrology core, but the connected HAN equipment must itself be double-isolated from mains. Aidon also says its CE compliance was tested with a maximum 3 m RJ12 cable.

So I would put the little transistor circuit and Waveshare board in an appropriate enclosed assembly rather than leaving a breadboard permanently connected to the meter.

One more thing before you build it

There is an important distinction between 7410 and 7550 system-module/data-profile support. Aidon's documentation confirms 7410 supports EFS2 from system-module software 1.2.143 onward, while the available profiles determine whether you receive EFS/DLMS binary or EFS2/IEC 62056-21 data.
 
For your 7550, I'd verify the exact system-module firmware/profile before we write the parser.

If you want, I can next give you 
a literal pin-by-pin wiring table (RJ12 → resistor → 2N3904 → Waveshare pins → GW4100 DB9) and 
a small test procedure using /dev/ttymxc2 so you can verify the circuit with a multimeter before plugging it into the meter.




