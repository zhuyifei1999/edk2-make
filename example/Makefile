obj-y += main.o

lib-y += MdePkg/BaseLib.a
lib-y += MdePkg/BasePrintLib.a
lib-y += MdePkg/UefiApplicationEntryPoint.a
lib-y += MdePkg/UefiBootServicesTableLib.a
lib-y += MdePkg/UefiMemoryAllocationLib.a
lib-y += MdePkg/UefiLib.a

lib-$(CONFIG_DEBUG) += MdePkg/BaseDebugPrintErrorLevelLib.a
lib-$(CONFIG_DEBUG) += MdePkg/UefiDebugLibConOut.a
ifneq ($(CONFIG_DEBUG),y)
lib-y += MdePkg/BaseDebugLibNull.a
endif

NAME = example

M=$(PWD)

include ../Makefile
