#include <Uefi.h>
#include <Library/DebugLib.h>
#include <Library/UefiApplicationEntryPoint.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/UefiLib.h>

EFI_STATUS
EFIAPI
UefiMain(
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  EFI_STATUS     Status;
  EFI_EVENT      TimerEvent;
  EFI_EVENT      WaitList[2];
  EFI_INPUT_KEY  Key;
  UINTN          Index;

  gST->ConOut->Reset(gST->ConOut, FALSE);

  Print(L"Hello, World!\n");
  Print(L"Press any key to continue...\n");

  Status = gBS->CreateEvent(EVT_TIMER, 0, NULL, NULL, &TimerEvent);
  ASSERT_EFI_ERROR(Status);

  Status = gBS->SetTimer(TimerEvent, TimerRelative, EFI_TIMER_PERIOD_SECONDS(5));
  ASSERT_EFI_ERROR(Status);

  WaitList[0] = gST->ConIn->WaitForKey;
  WaitList[1] = TimerEvent;

  Status = gBS->WaitForEvent(2, WaitList, &Index);
  ASSERT_EFI_ERROR(Status);

  if (Index == 0)
    gST->ConIn->ReadKeyStroke(gST->ConIn, &Key);

  gBS->CloseEvent(TimerEvent);

  return EFI_SUCCESS;
}
