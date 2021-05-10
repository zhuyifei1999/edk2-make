import configparser
import os
import uuid


M = os.environ['M']
O = os.environ['O']
EDK = os.environ['EDK']
ARCH = os.environ['ARCH']
NAME = os.environ['NAME']
LIBS = os.environ['LIBS'].split()


if '/' in NAME:
    PKG_NAME, MOD_NAME = NAME.split('/')
else:
    PKG_NAME, MOD_NAME = None, NAME


PCD_MODENAMESIZE = {
    'BOOLEAN': ('BOOL', 1),
    'UINT8': ('8', 1),
    'UINT16': ('16', 2),
    'UINT32': ('32', 4),
    'UINT64': ('64', 8),
}


def splitstrip(string, splitter):
    return [substring.strip() for substring in string.split(splitter)]


def openconf(path):
    config = configparser.ConfigParser(allow_no_value=True)
    config.optionxform = str
    if path:
        config.read(path)

    return config


def iteratesecs(conf, section):
    for sectionlst in conf:
        if section not in splitstrip(sectionlst, ','):
            continue

        yield sectionlst


def stripcomment(entry):
    if '#' not in entry:
        return entry

    return entry.split('#', 1)[0].strip()


def main():
    pcds = {}
    guids = {}
    mod_pcd = set()
    constructors = set()
    destructors = set()

    def do_pkg(pkg):
        dec = openconf(f'{EDK}/{pkg}/{pkg}.dec')
        dsc = openconf(f'{EDK}/{pkg}/{pkg}.dsc')

        def pcd_dec(section):
            for sectionlst in iteratesecs(dec, section):
                for entry in dec[sectionlst]:
                    name, value, typ, token = splitstrip(
                        stripcomment(entry), '|')

                    pcds[name] = [typ, value]

        pcd_dec('PcdsFeatureFlag')
        pcd_dec('PcdsFixedAtBuild')
        pcd_dec(f'PcdsFeatureFlag.{ARCH}')
        pcd_dec(f'PcdsFixedAtBuild.{ARCH}')

        def pcd_dsc(section):
            for sectionlst in iteratesecs(dsc, section):
                for entry in dsc[sectionlst]:
                    name, value = splitstrip(stripcomment(entry), '|')

                    pcds[name][1] = value

        pcd_dsc('PcdsFeatureFlag')
        pcd_dsc('PcdsFixedAtBuild')
        pcd_dsc(f'PcdsFeatureFlag.{ARCH}')
        pcd_dsc(f'PcdsFixedAtBuild.{ARCH}')

        def guid_dec(section):
            for sectionlst in iteratesecs(dec, section):
                for name, value in dec[sectionlst].items():
                    guids[name] = value

        guid_dec('Guids')
        guid_dec(f'Guids.{ARCH}')
        # guid_dec('Ppis')
        # guid_dec(f'Ppis.{ARCH}')
        guid_dec('Protocols')
        guid_dec(f'Protocols.{ARCH}')

    def do_mod(pkg, mod):
        inf = openconf(f'{EDK}/{pkg}/Library/{mod}/{mod}.inf')

        def pdc_mod(section):
            for sectionlst in iteratesecs(inf, section):
                for entry in inf[sectionlst]:
                    mod_pcd.add(stripcomment(entry))

        pdc_mod('FeaturePcd')
        pdc_mod('Pcd')
        pdc_mod(f'FeaturePcd.{ARCH}')
        pdc_mod(f'Pcd.{ARCH}')

        if 'CONSTRUCTOR' in inf['Defines']:
            constructors.add(inf['Defines']['CONSTRUCTOR'])

        if 'DESTRUCTOR' in inf['Defines']:
            destructors.add(inf['Defines']['DESTRUCTOR'])

        return inf

    if PKG_NAME:
        do_pkg(PKG_NAME)
        inf = do_mod(PKG_NAME, MOD_NAME)
        modguid = inf['Defines']['FILE_GUID']
    else:
        if os.path.exists(f'{O}/AutoGen.uuid'):
            with open(f'{O}/AutoGen.uuid', 'r') as f:
                modguid = f.read()
        else:
            modguid = str(uuid.uuid4())
            with open(f'{O}/AutoGen.uuid', 'w') as f:
                f.write(modguid)

        for lib in LIBS:
            do_mod(*lib.split('.')[0].split('/'))

        for pkg in set(lib.split('/')[0] for lib in LIBS):
            do_pkg(pkg)

        inf = openconf(None)

    with open(f'{O}/AutoGen.h', 'w') as f:
        f.write(f'''\
/**
  DO NOT EDIT
  FILE auto-generated
**/

#ifndef _AUTOGENH_{modguid.replace('-', '_')}
#define _AUTOGENH_{modguid.replace('-', '_')}

#include <Base.h>
#include <Library/PcdLib.h>
#include <Uefi.h>

extern GUID  gEfiCallerIdGuid;
extern GUID  gEdkiiDscPlatformGuid;
extern CHAR8 *gEfiCallerBaseName;
''')

        if PKG_NAME:
            for name in mod_pcd:
                typ, value = pcds[name]
                _, name = name.split('.')
                modename, size = PCD_MODENAMESIZE[typ]

                f.write(f'''\
#define _PCD_TOKEN_{name}  0U
extern const {typ} _gPcd_FixedAtBuild_{name};
#define _PCD_GET_MODE_{modename}_{name}  _gPcd_FixedAtBuild_{name}
#define _PCD_VALUE_{name} {value}
#define _PCD_SIZE_{name} {size}
#define _PCD_GET_MODE_SIZE_{name} _PCD_SIZE_{name}
''')
        else:
            f.write('''
EFI_STATUS
EFIAPI
UefiMain (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  );
''')

        f.write('#endif\n')

    with open(f'{O}/AutoGen.make', 'w') as f:
        def source(section):
            for sectionlst in iteratesecs(inf, section):
                for entry in inf[sectionlst]:
                    if '|' in entry:
                        entry, compiler = splitstrip(entry, '|')

                        if compiler.upper() != 'GCC':
                            continue

                    filename, ext = entry.split('.')
                    if ext == 'h':
                        continue
                    elif ext in ['c', 'nasm']:
                        f.write(f'obj-y += {filename}.o\n')
                    else:
                        raise ValueError(ext)

        source('Sources')
        source(f'Sources.{ARCH}')

        if not PKG_NAME:
            f.write('obj-y += AutoGen.obj\n')

    if not PKG_NAME:
        with open(f'{O}/AutoGen.c', 'w') as f:
            f.write('''\
/**
  DO NOT EDIT
  FILE auto-generated
**/

#include <Uefi.h>
#include <Library/BaseLib.h>
#include <Library/DebugLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/UefiApplicationEntryPoint.h>
''')

            guidpy = uuid.UUID(modguid)
            (time_low, time_mid, time_hi_version,
             clock_seq_hi_variant, clock_seq_low, node) = guidpy.fields
            f.write(f'GLOBAL_REMOVE_IF_UNREFERENCED GUID gEfiCallerIdGuid = {{'
                    f'0x{time_low:08x}, '
                    f'0x{time_mid:04x}, 0x{time_hi_version:04x}, {{'
                    f'0x{clock_seq_hi_variant:02x}, '
                    f'0x{clock_seq_low:02x}, '
                    f'0x{((node >> 40) & 0xff):02x}, '
                    f'0x{((node >> 32) & 0xff):02x}, '
                    f'0x{((node >> 24) & 0xff):02x}, '
                    f'0x{((node >> 16) & 0xff):02x}, '
                    f'0x{((node >> 8) & 0xff):02x}, '
                    f'0x{((node >> 0) & 0xff):02x}}}}};\n')

            f.write(f'GLOBAL_REMOVE_IF_UNREFERENCED CHAR8 *gEfiCallerBaseName'
                    f' = "{NAME}";\n')

            for name, value in guids.items():
                f.write(f'GLOBAL_REMOVE_IF_UNREFERENCED EFI_GUID '
                        f'{name} = {value};\n')

            for name in mod_pcd:
                typ, value = pcds[name]

                # FIXME: See
                # https://edk2-docs.gitbook.io/edk-ii-dec-specification/3_edk_ii_dec_file_format/310_pcd_sections
                if typ in ['VOID*']:
                    continue

                _, name = name.split('.')
                modename, size = PCD_MODENAMESIZE[typ]

                f.write(f'''\
#define _PCD_TOKEN_{name}  0U
#define _PCD_SIZE_{name} {size}
#define _PCD_GET_MODE_SIZE_{name} _PCD_SIZE_{name}
#define _PCD_VALUE_{name} {value}
GLOBAL_REMOVE_IF_UNREFERENCED const {typ} _gPcd_FixedAtBuild_{name} = _PCD_VALUE_{name};
extern const {typ} _gPcd_FixedAtBuild_{name};
#define _PCD_GET_MODE_{modename}_{name}  _gPcd_FixedAtBuild_{name}
''')

            for name in {*constructors, *destructors}:
                f.write(f'''\
EFI_STATUS
EFIAPI
{name} (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  );
''')

            f.write('''
VOID
EFIAPI
ProcessLibraryConstructorList (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
''')
            if constructors:
                f.write('  EFI_STATUS  Status;\n')
            for name in constructors:
                f.write(f'''
  Status = {name} (ImageHandle, SystemTable);
  ASSERT_EFI_ERROR (Status);
''')

            f.write('}\n')

            f.write('''
VOID
EFIAPI
ProcessLibraryDestructorList (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
''')
            if destructors:
                f.write('  EFI_STATUS  Status;\n')
            for name in destructors:
                f.write(f'''
  Status = {name} (ImageHandle, SystemTable);
  ASSERT_EFI_ERROR (Status);
''')

            f.write('}\n')

            f.write('''
const UINT32 _gUefiDriverRevision = 0x00000000U;

EFI_STATUS
EFIAPI
ProcessModuleEntryPointList (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  return UefiMain (ImageHandle, SystemTable);
}
''')


if __name__ == '__main__':
    main()
