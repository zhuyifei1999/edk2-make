SRC += main.c

LIBS += MdePkg/BaseLib.a
LIBS += MdePkg/BasePrintLib.a
LIBS += MdePkg/UefiApplicationEntryPoint.a
LIBS += MdePkg/UefiBootServicesTableLib.a
LIBS += MdePkg/UefiMemoryAllocationLib.a
LIBS += MdePkg/UefiLib.a

ifeq ($(DEBUG),1)
    LIBS += MdePkg/BaseDebugPrintErrorLevelLib.a
    LIBS += MdePkg/UefiDebugLibConOut.a
else
    LIBS += MdePkg/BaseDebugLibNull.a
endif

NAME = example

M=$(PWD)

include ../Makefile
