#
#   Copyright (c) 2021 Christof Ruch. All rights reserved.
#
#   Dual licensed: Distributed under Affero GPL license by default, an MIT license is available for purchase
#
import hashlib


def name():
    return "Alesis Andromeda A6"


def createDeviceDetectMessage(channel):
    # The A6 replies to Universal Device Inquiry, p. 6 of the "Sysex specs" document
    return [0xf0, 0x7e, 0x7f, 0x06, 0x01, 0xf7]


def deviceDetectWaitMilliseconds():
    return 500


def needsChannelSpecificDetection():
    return False


def channelIfValidDeviceResponse(message):
    # Check for reply on Universal Device Inquiry
    if len(message) > 12 and message[:12] == [0xf0, 0x7e, 0x7f, 0x06, 0x02, 0x00, 0x00, 0x0e, 0x1d, 0x00, 0x00, 0x00]:
        # Just return any valid channel
        return 0x00
    return -1


def numberOfBanks():
    return 16


def numberOfPatchesPerBank():
    return 128


#
# Implementation for Edit Buffer commented out because there seems to be a bug that the edit buffer does indeed not work
# https://www.gearslutz.com/board/showpost.php?p=15188863&postcount=623
#def createEditBufferRequest(channel):
#    # Sysex documentation specifies an edit buffer exists
#    # Edit buffer #16 (decimal) is called the program edit buffer
#    return [0xf0, 0x00, 0x00, 0x0e, 0x1d, 0x03, 16, 0xf7]
#
#
#def isEditBufferDump(message):
#    return len(message) > 6 and message[:7] == [0xf0, 0x00, 0x00, 0x0e, 0x1d, 0x02, 16]
#
#
#def convertToEditBuffer(channel, message):
#    if isEditBufferDump(message):
#        return message
#    if isSingleProgramDump(message):
#        return [0xf0, 0x00, 0x00, 0x0e, 0x1d, 0x02, 16] + message[8:]
#    raise Exception("This is neither an edit buffer nor a program buffer - can't be converted")


def createProgramDumpRequest(channel, program_number):
    bank = program_number // numberOfPatchesPerBank()
    program = program_number % numberOfPatchesPerBank()
    return [0xF0, 0x00, 0x00, 0x0E, 0x1D, 0x01, bank, program, 0xf7]


def isSingleProgramDump(message):
    return len(message) > 5 and message[:6] == [0xF0, 0x00, 0x00, 0x0E, 0x1D, 0x00]


def convertToProgramDump(channel, message, program_number):
    bank = program_number // numberOfPatchesPerBank()
    program = program_number % numberOfPatchesPerBank()
#    if isEditBufferDump(message):
#        return [0xF0, 0x00, 0x00, 0x0E, 0x1D, 0x00, bank, program] + message[7:]
    if isSingleProgramDump(message):
        # We just need to adjust bank and program and position 6 and 7
        return message[:6] + [bank, program] + message[8:]
    raise Exception("Can only create program dumps from master keyboard dumps")


def nameFromDump(message):
    if isSingleProgramDump(message):
        data_block = unescapeSysex(message[8:-1])  # The data block starts at index 8, and does not include the 0xf7
        return ''.join([chr(x) for x in data_block[2:2 + 16]])
    raise Exception("Can only extract name from master keyboard program dump")


def createBankDumpRequest(channel, bank):
    # Page 4 of the sysex spec
    return [0xf0, 0x00, 0x00, 0x0e, 0x1d, 0x0a, bank, 0xf7]


def isPartOfBankDump(message):
    # A bank dump on the A6 consists of 128 single dumps
    return isSingleProgramDump(message)


def isBankDumpFinished(messages):
    for message in messages:
        if isPartOfBankDump(message):
            return True
    return False


def extractPatchesFromBank(message):
    if isSingleProgramDump(message):
        return [message]
    return []


def calculateFingerprint(message):
    if isSingleProgramDump(message):
        data_block = unescapeSysex(message[8:-1])  # The data block starts at index 8, and does not include the 0xf7
        # Blank out name
        data_block[2:2 + 16] = [0] * 16
        return hashlib.md5(bytearray(data_block)).hexdigest()  # Calculate the fingerprint from the cleaned payload data
    # Don't know why we should come here, but to be safe, just hash all bytes
    return hashlib.md5(bytearray(message)).hexdigest()


def friendlyBankName(bank):
    return ["User", "Preset1", "Preset2", "Card 1", "Card 2", "Card 3", "Card 4", "Card 5", "Card 6", "Card 7",
            "Card 8", "Card 9", "Card 10", "Card 11", "Card 12", "Card 13"][bank]


def friendlyProgramName(patchNo):
    bank = patchNo // numberOfPatchesPerBank()
    program = patchNo % numberOfPatchesPerBank()
    return friendlyBankName(bank) + " %03d" % program


def unescapeSysex(data):
    # The A6 uses the shift technique to store 8 bits in 7 bits. This is some particularly ugly code I could only
    # get to work with the help of the tests
    result = []
    roll_over = 0
    i = 0
    while i < len(data) - 1:
        mask1 = (0xFF << roll_over) & 0x7F
        mask2 = 0xFF >> (7 - roll_over)
        result.append((data[i] & mask1) >> roll_over | (data[i + 1] & mask2) << (7 - roll_over))
        roll_over = (roll_over + 1) % 7
        i = i + 1
        if roll_over == 0:
            i = i + 1
    return result


import binascii

if __name__ == "__main__":
    # Some tests
    assert friendlyBankName(4) == "Card 2"
    assert friendlyProgramName(128) == "Preset1 000"
    assert createProgramDumpRequest(1, 257) == [0xF0, 0x00, 0x00, 0x0E, 0x1D, 0x01, 2, 1, 0xf7]
    single_program = "F000000E1D00000026150812172C1A3720020D23174D5D347472010172003C0000364014000400000001780105000040003800010000000000000000000000000000000000000000000038010E0000000000000000000000000000000000405240164336460C200040507C795F067C1F7F31400108000000000138010E6001000C000000002048030016000002041400007E7D3F102000000000000000000000000000080009030005000000000000000000000000605F7F010004080000000000000000000000007F7E07001020000000000000000000000000043844014002000000000000000000000000706F7F000002040000000000000000000000403F7F030008100000000000000000000000007E7D0F00204000000000000000000000000078773F000001020000000000000000000000605F7F010004080000000000000000000000007F7E070010200000000000000000000000007C7B1F00400001000000000000007A410000706F7F070002000000000000000018020800403F7F1F00080000000000000000501D3400007E7D6F00200000000000000000000000000078773F000001020000000000000022400100605F7F030004000000000000000060011800007F7E3F00100000000000000000203C7800007C7B7F214000000000000000000000000000706F7F00000204000000000000007C7B0F00403F7F0700081000000000000000400A3400007E7D4F00200000000000000000000000000078773F000001020000000000000000000000605F7F010004080000000000000000000000007F7E070010200000000000000000000000007C7B1F004000010000000000000000000000706F7F000102040000000000000000000000403F7F030008100000000000000000000000007E7D0F00204000000000000000000000000078773F000001020000000000000000000000605F7F100004000000000000000000000000007F7E430010000000000000000000000000007C7B1F004000000000000000000031004B07746F7F000002000000000000000060420A00403F7F030008000000000000000000000000007E7D0F0020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002000000100040010407F740100784F1F000000000000000000000100000010000000000200000000407F7801040000004000000000080000000001000000100000000002000000200000000000780F1F4000000000080000000001003C000000000000034414217448593408132A5D4A3933776F213818032615297768653439176E6E5A7F7B0F30404812440E194B067122552D193F761E1E040833645422754E5D4C18776A6D4D7B3F7F7F7D07002003000F000000000000000000000000000000000000000060016E0D010070011640200000000000200000000000000003200043020410100000000000000000000000000000000000000041125E011028621B000A442607000040000620070000000000020000000000001800021014200001010000000000000000000000000000000000000000000000000000005020343A0000000470003400000000001000000000000040011800240102080800000000000000000000000000000000000000000002001003400C60004002000000100000020028707F3F0000000000000000000000000000000000000000000000000000010002400F0A0000547C0600404002000A0C001020000142020408004001003C00000000000000000000000000000000000000002040007C06182A066A1430094A030000200000057E7F07000000000000000000000000000000000000000000000000500C140D3001000000406A6F000C14084000410102020410202840000100180040070000000000000000000000000000000000000000040000004026780118460E0000400000040040647F7F00000000000000000000000000000000000000000000000000000230041D0000000028790C4001010600142000204000022405081040010300780000000000000000000000000000000000001009000000000000706F3F000000301800000701030400000000000000000000000000000074030000000000003004000000000000000000000040006201000000000000000C000002030C0610003030011203600026600049013000183040670042053800184C004001245840594272041A6000386125020D30005F307300360A7224784720660752027C5D3032410170044013004E0038024009002600180160044012004A0040024009002600180160044013000000000000400811224408112244080000007810607F1700040800202027000000000000000000000000000000000000480100000000200000180060464000010000000020401700040800000000000000000000000000000000000000400E0000000000000100681D04000000000000000000600354183000000000000000000000400C007201000000000000000000000000000000000000000000607F7F000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000007E7F5702020000000000005141400100467D07004016000A002820010A000000000000400C407F50000000000040000001000030204003000008000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000F7"
    single = list(binascii.unhexlify(single_program))
    assert isSingleProgramDump(single)

    test_data = [0x7f, 0x01, 0x02, 0x00]
    raw = unescapeSysex(test_data)
    assert raw == [0xff, 0x80, 0x00]
    print(nameFromDump(single))

    test_data = [0x7f] * 16
    assert unescapeSysex(test_data) == [0xff] * 14
    test_data = [0x00] * 16
    assert unescapeSysex(test_data) == [0x00] * 14
    test_data = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x7f, 0x00, 0x00]
    assert unescapeSysex(test_data) == [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00]

    # second_program = "F000000E1D00000126155472364D5B37775C0161144D5932665E496B0600400F0053405A020808480000000000000040005E00050000000000000000000000000000000000000000000038010E0000000000000000000000000000000000002700200235666C2E5E000000000000401F7F01000008000000000038010E2000000C000000002025280028100004000000007E7D0F002040000000000000000000400000080010030007000000000000000032000600605F7F100004080000000000000000000000007F7E0700102000000000000000203B280000040018024003000000000000000065210100706F7F080202000000000000000048000000403F7F050008000000000000000000000000007E7D0F00204000000000000000000000000078773F000001020000000000000000000000605F7F0100040800000000000000280E0600007F7E0B0010200000000000000000000000007C7B1F004000010000000000000078010100706F7F02000204000000000000004C000700403F7F210008000000000000000000450500007E7D4F00200000000000000000400C10010078777F000001000000000000000076030100605F7F070004000000000000000070001A00007F7E230010000000000000000040036800007C7B0F024000000000000000000000000000706F7F000002040000000000000030070000403F7F050008100000000000000010003C00007E7D2F00204000000000000000000000000078773F000001020000000000000056400300605F7F0E0004080000000000000068000C00007F7E170010000000000000000060091800007C7B5F014000010000000000000000000000706F7F000102040000000000000000000000403F7F030008100000000000000050071800007E7D0701204000000000000000407700000078771F040001000000000000000000000000605F7F100004000000000000000000000000007F7E430010000000000000000020000858417C7B1F004000000000000000000007301307726F7F00000200000000000000007C7B0F00403F7F030008000000000000000000000000007E7D0F0020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002000000100040010407F740100000000000E000000000000000001003C0010000000000200000020000000000400000040000000000800000000007E630710000000000200000020000000000400000040000000000800000000007E6307000000007F7E3B6B5E0B37264B7768551235064C080E5E3F675C596A5508131A3B4628111123000C0030404812440E194B067122552D193F761E1E040833645422754E5D4C18776A6D4D7B3F7F7F7D07002003010F00000000000000000000000000000000000000002041234100007843094030000000000020000220010000000320004302041030400000000000000000000000000000000000000D7A150420033E1A0008601809000000000074030000000000025400080000001800021812200001050400000000000000000000000000000000000000000000000000005020343A00007C7F0F400B0000000000100000000000003000100024030208080000000000000000000000000000000000204032005C166804004075305003060000100000026C5B7F7F7F23700000000000000000000000000000000000000000000000000120037C6F3F0000547C0600404002000A0C1812200001410A0408704001003C00000000000000000000000000000000000000006000000F014C1C0D2C2400013C680303207E7F7F7F7F0718600910680002000000000000000000000000000000000000104008007E7D0700400A67000004000000010412020410106A000105020C384007000000000000000000000000000000000000000028004016000077417E7F0F0000646000540040647F7F7F7E030C000000000000000000000000000000000000000000000278771F0000000028790C4001010000102000204000022415181060410000780000000000000000000000000000000000001009000000000000706F3F000000181800000701030000000000000000000000000000000158000000000000003004000000000000000000000000003200000000000000000C000000000000000E00600016000007004E000E000000000000000000045800004C0003000068602C433E0D20213024406C0641107020405C40044047362800781C0505004F205000700100074023001201080C00180030000406601F0037002000080300040019004000601F0008000000000000400001020408102040000000007810607F1700040800202026000000000000000000000000000000000000480100000000200000180050464000010000002040401700040800000000000000000000000000000000000000407B0000000000000100685D0000000000000000000060052E143801000000000000000000400C407201000000000000000000000000000000000000000000002C3800000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000050010E00000000000001604415327E1323360819104101700100000023000000000000000000000000000040004000000030200001000008000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000F7"
    second_program = "F000000E1D00000226155042560C082861680D4306245337644A01010200000000604078711200000000000000000040002E20040000000000000000000000000000000000000000000038010E0000000000000000000000000000000000004000000230660C200000007C790F00401F7F336008041A00003F703B010E2001000C000000002051030022000031091800007E7D2F00200000000000000000407F7E0100080010030007020000000000000000000000605F7F010004080000000000000000000000007F7E07001020000000000000000035281E00050038204003010000000000000000000000706F7F000002040000000000000000000000403F7F030008100000000000000070673F00007E7D3F00204000000000000000000000000078773F00000102000000000000002E020500605F7F020004000000000000000000000000007F7E0700102000000000000000400A3000007C7B7F00400000000000000000001C200300706F7F03000200000000000000006C063F00783F7F130008100000000000000000300000007E7D4F10204000000000000000400720000078773F030001000000000000000072430500605F7F160004000000000000000050010E00007F7E0F00100000000000000000403D3800007C7B3F20400001000000000000001A600200706F7F040002000000000000000000000000403F7F030008100000000000000000023800007E7D3F00200000000000000000000000000078773F00000102000000000000002C430500605F7F090004000000000000000000000000007F7E070010200000000000000000000000007C7B1F00400001000000000000007F7E0300706F3F01020200000000000000007C730F00403F7F050008100000000000000060073400007E7D3F00204000000000000000000000000078773F000001020000000000000000000000605F7F100004000000000000000000000000007F7E430010000000000000000000034800007C7B1F004000000000000000000030700100706F7F000002000000000000000060010600403F7F030008000000000000000000000000007E7D0F0020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002000000100040010407F740100000000000000000000000000000100000010000000000200000000407F7801040000004000000000080000000001000000100000000002000000200000000000780F1F4000000000080000000001003C000000000000034414217448593408132A5D4A3933776F213818032615297768653439176E6E5A7F7B0F30404812440E194B067122552D193F761E1E040833645422754E5D4C18776A6D4D7B3F7F7F7D07002003000F000000000000000000000000000000000000000000001948010000025A420A000000000020000000000000000320006302041010000000000000000000000000000000000000000F7A1E0000021C6B000A44260700003A101D7C030000000000020000000000001804425616200001010000000000000000000000000000000000000000000000000000005020343A0000000470003400000000001000000000000040011800240102080800000000000000000000000000000000000000000002001003404C5A100102000000100000020028707F3F0000000000000000000000000000000000000000000000000000015401490F0A0000547C0600404002000A0C001020000142020408004001003C000000000000000000000000000000000000000020000034035027090C1F18005A020000200000057E7F3F0E02000000000000000000000000000000000000000000000010000A6022400500404A6F000C14081000410103020410206840000106180040070000000000000000000000000000000000000000040000204349780124060E0000400000000140647F7F00000000000000000000000000000000000000000000000000000248041C0228000028790C4001010600142000204000022405081040010300780000000000000000000000000000000000001009000000000000706F3F000000181800000701030000000000000000000000000000000074030000000000003004000000000000000000000000003200000000000000000C30004701240C10194064001403681B0063004201340630310062005208380C205B000A032400024400190450185001410905061870704057006D0248141064411A00700430222045000040024012000E00180160090006001C0130024013001000580060090028004C005004000A000000000000400811224408102244080000007810607F17000408002020260000000000000000000000000000000000004801000000002000001800204940600100000000607F170004080000000000000000000000000000000000000040050000000000000100681D000000000000000000004004360A4001000000000000000000400C007201000000000000000000000000000000000000000000607F7F000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000007E7F2F031E000000000000514100010332255702405170630000000000000000000000400C407F63000000000040000000005030204001000008000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000F7"
    real_program = "f000000e1d00000026155042560c0822724a056b060408102040000102000000007e00560242027c0000000450042200000002000000000000000000000000000000000000000000000038010e00000000000000000000000000000000000040303d437e471a200b2e700100700512000000000008000000000138010e2000000c000000002031040018000104000000007e7d0f00204000000000000000407f5f010000001e030007000000000000000000000000605f7f010004080000000000000000000000007f7e0700102000000000000000607f62000000004f01400300000000000000002b400300706f3f080202000000000000000000000000403f7f030008100000000000000000000000007e7d0f00204000000000000000000000000078773f000001020000000000000000000000605f7f010004080000000000000000000000007f7e070010200000000000000000000000007c7b1f00400001000000000000004a210000706f3f01000200000000000000003c000d00403f7f050408000000000000000000450500007e7d4f00200000000000000000407c60000078775f40000100000000000000007e400100605f7f0d00040000000000000000300d1400007f7e1f0810200000000000000000000000007c7b1f004000010000000000000000000000706f7f000002040000000000000030070000403f7f050008000000000000000000000000007e7d0f00204000000000000000000000000078773f00000102000000000000003c400000605f7f0e0004000000000000000068031400007f7e0b0010200000000000000060091800007c7b5f014000000000000000000000000000706f7f000102040000000000000000000000403f7f030008100000000000000050071800007e7d070120400000000000000040155b010078771f040001020000000000000000000000605f7f100004000000000000000000000000007f7e430010000000000000000000083800007c7b1f004000000000000000000016102b69736f7f000002000000000000000070000f00403f7f030008000000000000000000000000007e7d0f00200000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000020000001000400100000007e73070000000000040000000000000100000010000000000200000000407f7801040000004000000000080000000001000000100000000002000000200000000000780f1f4000000000080000000001003c000000000000034414217448593408132a5d4a3933776f213818032615297768653439176e6e5a7f7b0f30404812440e194b067122552d193f761e1e040833645422754e5d4c18776a6d4d7b3f7f7f7d07002003000f00000000000000000000000000000000000000002041234100007843094030000000000020000000000000000320004302041070400000000000000000000000000000000000000d7a150420033e1a000054310f000040001274030000000000020000000000001800022014200001010000000000000000000000000000000000000000000000000000005020343a00007c7f0f400b00000000001000000000000030001000240302080800000000000000000000000000000000000000000002001003400c60004002000000100000020028707f3f00000000000000000000000000000000000000000000000000000100010000000000543c7e0f404002000a0c001020000151020408004001003c00000000000000000000000000000000000000002040005c076c207b03091801306c0304405c7f7f7f7f0700000000000000000000000000000000000000000000000040044c2d5061400400406a677f0104000000010000020410102a40000100180040070000000000000000000000000000000000000000400040434440774166460c4038646006140040647f7f0000000000000000000000000000000000000000000000000000024805790d70000028790c0001010000002000204000022405081040010300780000000000000000000000000000000000001009000000000000706f3f000000181800000701030000000000000000000000000000000060030000000000003004000000000000000000000000003200000000000000000c0000000000000c003000000000000000000000000000000000000000000000000000000000003c0070014007001e0078006003000f003c0070014007001e0078006003000f003c007001000200080020000001000400100040000002000800200000010004001000400000020008000000000000400811224408112244080000001810607f170004080020002400000000000000000000000000000000000048010000000020000018003044000001000000300040170004080000000000000000000000000000000000000040210000000000000100681d0000000000000000000010032e094201000000000000000000400c007201000000000000000000000000000000000000000000607f7f000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000b1000000000000000400c0d0700765a35081940000170010000403100000000400c407f50000000000040000000000030200001000018200000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000f7"
    second = list(binascii.unhexlify(real_program))
    print(nameFromDump(second))