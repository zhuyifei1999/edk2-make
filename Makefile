M := $(CURDIR)
O := $(M)/Build

BASE_O ?= $(O)

ARCH ?= X64
MODULE_TYPE ?= UEFI_APPLICATION

ifeq ($(NAME),)
$(error Define NAME)
endif

BASE_NAME := $(notdir $(NAME))

DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
EDK := $(DIR)edk2
IMAGE_ENTRY_POINT := _ModuleEntryPoint

COMMA := ,

-include $(O)/AutoGen.make

OBJ := $(patsubst %,$(O)/%.o,$(filter-out AutoGen.c,$(SRC))) \
	$(patsubst %.c,$(O)/%.obj,$(filter AutoGen.c,$(SRC)))

SRC := $(patsubst %,$(M)/%,$(filter-out AutoGen.c,$(SRC))) \
	$(patsubst %,$(O)/%,$(filter AutoGen.c,$(SRC)))

define uniq =
	$(eval seen :=)
	$(foreach _,$1,$(if $(filter $_,${seen}),,$(eval seen += $_)))
	${seen}
endef

CC := gcc
AR := gcc-ar
OBJCOPY := objcopy
NASM := nasm
PYTHON := python
GENFW := $(EDK)/BaseTools/Source/C/bin/GenFw
TRIM := $(EDK)/BaseTools/BinWrappers/PosixLike/Trim

LIB_PKG = $(call uniq,MdePkg/ $(dir $(LIBS)))
INCLUDES := \
	-I$(M) \
	-I$(O) \
	$(LIB_PKG:%=-I$(EDK)/%) \
	$(LIB_PKG:%=-I$(EDK)/%Include) \
	$(LIB_PKG:%=-I$(EDK)/%Include/$(ARCH))

PPFLAGS := -E -x assembler-with-cpp -include AutoGen.h

ifeq ($(ARCH),X64)
	CFLAGS := \
		-g -Os -fshort-wchar -fno-builtin -fno-strict-aliasing -Wall -Werror \
		-Wno-array-bounds -include AutoGen.h -fno-common -ffunction-sections -fdata-sections \
		-m64 -fno-stack-protector "-DEFIAPI=__attribute__((ms_abi))" \
		-maccumulate-outgoing-args -mno-red-zone -Wno-address -mcmodel=small \
		-fpie -fno-asynchronous-unwind-tables -Wno-address -flto -DUSING_LTO -Os \
		-Wno-unused-but-set-variable -Wno-unused-const-variable

	NASM_FLAGS := -f elf64

	LDFLAGS := \
		-nostdlib -Wl,-n,-q,--gc-sections -z common-page-size=0x40 \
		-Wl,--entry,$(IMAGE_ENTRY_POINT) -u $(IMAGE_ENTRY_POINT) \
		-Wl,-Map,$(O)/$(BASE_NAME).map,--whole-archive \
		-Wl,-melf_x86_64,--oformat=elf64-x86-64,-pie \
		-flto -Os

	LDFLAGS2 := -Wl,--defsym=PECOFF_HEADER_SIZE=0x228 \
		-Wl,--script=$(EDK)/BaseTools/Scripts/GccBase.lds \
		-Wno-error
else
$(error Bad ARCH)
endif

ifeq ($(V),1)
	Q =
	msg =
else
	Q = @
	msg = @printf '  %-8s %s%s%s\n' \
		      "$(1)" \
			  "$(if $(and $(filter-out CLEAN,$(1)),$(filter-out MAKE,$(1)),$(filter-out DESCEND,$(1)),$(filter-out QEMU,$(1))),$(NAME)$(if $(2),:))" \
		      "$(patsubst $(O)/%,%,$(2))" \
		      "$(if $(3), $(3))";
	MAKEFLAGS += --no-print-directory
endif

all: $(O)/$(BASE_NAME).efi

-include $(OBJ:%=%.deps)

.PHONY: run clean basetools basetools-clean
.SECONDARY:
.DELETE_ON_ERROR:

clean:
	$(call msg,CLEAN)
	$(Q)test -d $(O) && find $(O) -name 'AutoGen.*' -delete || true
	$(Q)test -d $(O) && find $(O) -name '*.o' -delete || true
	$(Q)test -d $(O) && find $(O) -name '*.o.deps' -delete || true
	$(Q)test -d $(O) && find $(O) -name '*.i' -delete || true
	$(Q)test -d $(O) && find $(O) -name '*.ii' -delete || true
	$(Q)test -d $(O) && find $(O) -name '*.iii' -delete || true
	$(Q)test -d $(O) && find $(O) -name '*.a' -delete || true
	$(Q)test -d $(O) && find $(O) -name '*.so' -delete || true
	$(Q)test -d $(O) && find $(O) -name '*.map' -delete || true
	$(Q)test -d $(O) && find $(O) -name '*.debug' -delete || true
	$(Q)test -d $(O) && find $(O) -name '*.txt' -delete || true
	$(Q)test -d $(O) && find $(O) -name '*.efi' -delete || true
	$(Q)test -d $(O) && find $(O) -type d -empty -delete || true

basetools-clean:
	$(call msg,MAKE,$(EDK)/BaseTools/Source/C,clean)
	$(Q)$(MAKE) -s -C $(EDK)/BaseTools/Source/C clean

basetools: $(EDK)/BaseTools/Source/C/bin/GenFw

$(EDK)/BaseTools/Source/C/bin/GenFw:
	$(call msg,MAKE,$(EDK)/BaseTools/Source/C)
	$(Q)make -s -C $(EDK)/BaseTools/Source/C

$(O):
	$(Q)mkdir -p $@

$(O)/AutoGen.guid:

$(O)/AutoGen.c $(O)/AutoGen.h $(O)/AutoGen.make: $(O)/AutoGen.guid | $(O)
	$(call msg,GEN)
	$(Q)PYTHONPATH=$(EDK)/BaseTools/Source/Python \
		M=$(M) \
		O=$(O) \
		EDK=$(EDK) \
		NAME=$(NAME) \
		ARCH=$(ARCH) \
		LIBS="$(LIBS)" \
		$(PYTHON) $(DIR)_AutoGen.py

$(O)/%.c.o: $(M)/%.c $(O)/AutoGen.h | $(O)
	$(Q)mkdir -p $(@D)
	$(call msg,CC,$@)
	$(Q)$(CC) -MMD -MF $@.deps $(CFLAGS) -c -o $@ $(INCLUDES) $<

$(O)/AutoGen.obj: $(O)/AutoGen.c $(O)/AutoGen.h | $(O)
	$(Q)mkdir -p $(@D)
	$(call msg,CC,$@)
	$(Q)$(CC) -MMD -MF $@.deps $(CFLAGS) -c -o $@ $(INCLUDES) $<

# $(O)/inc.lst: | $(O)
# 	$(call msg,GEN,$@)
# 	$(Q)echo $(INCLUDES) | tr ' ' '\n' > $@

$(O)/%.nasm.o: $(M)/%.nasm $(O)/AutoGen.h | $(TRIM)
	$(Q)mkdir -p $(@D)
	$(call msg,NASM,$@)
	$(Q)#$(TRIM) --asm-file -o $(O)/$*.i -i $(O)/inc.lst $<
	$(Q)$(CC) -MMD -MF $@.deps $(PPFLAGS) $(INCLUDES) $< > $(O)/$*.ii
	$(Q)$(TRIM) --trim-long --source-code -o $(O)/$*.iii $(O)/$*.ii
	$(Q)$(NASM) $(INCLUDES) $(NASM_FLAGS) -o $@ $(O)/$*.iii

$(O)/$(BASE_NAME).a: $(OBJ) | $(O)
	$(call msg,AR,$@)
	$(Q)$(AR) cr $@ $^

$(BASE_O)/%.a: | $(O)
	$(call msg,DESCEND,$@)
	$(Q)$(MAKE) \
		-f $(DIR)Makefile \
		-C $(EDK)/$(dir $*)Library/$(notdir $*) \
		M=$(EDK)/$(dir $*)Library/$(notdir $*) \
		O=$(BASE_O)/$* \
		BASE_O=$(BASE_O) \
		LIB= \
		NAME=$* \
		$(BASE_O)/$*/$(notdir $*).a
	$(Q)cp $(BASE_O)/$*/$(notdir $*).a $@

$(O)/$(BASE_NAME).so: $(O)/$(BASE_NAME).a $(LIBS:%=$(O)/%)
	$(call msg,LD,$@)
	$(Q)$(CC) -o $@ $(LDFLAGS) -Wl,--start-group $(addprefix -Wl$(COMMA),$^) -Wl,--end-group $(CFLAGS) $(LDFLAGS2)
	$(call msg,CP,$(patsubst %.so,%.debug,$@))
	$(Q)cp -f $@ $(patsubst %.so,%.debug,$@)
	$(call msg,STRIP,$@)
	$(Q)$(OBJCOPY) --strip-unneeded -R .eh_frame $@

$(O)/$(BASE_NAME).efi: $(O)/$(BASE_NAME).so | $(GENFW)
	$(call msg,GENFW,$@)
	$(Q)$(GENFW) -e $(MODULE_TYPE) -o $@ $<

run: | $(O)/$(BASE_NAME).efi
	$(call msg,QEMU,$|)
	$(Q)$(DIR)testqemu.sh $|
