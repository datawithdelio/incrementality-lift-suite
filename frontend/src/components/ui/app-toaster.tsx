"use client";

import { CheckCircleIcon } from "@phosphor-icons/react/CheckCircle";
import { InfoIcon } from "@phosphor-icons/react/Info";
import { WarningCircleIcon } from "@phosphor-icons/react/WarningCircle";
import { XCircleIcon } from "@phosphor-icons/react/XCircle";
import { Toaster } from "sonner";

export function AppToaster() {
  return (
    <Toaster
      position="top-right"
      closeButton
      visibleToasts={4}
      gap={10}
      icons={{
        success: <CheckCircleIcon weight="fill" aria-hidden="true" />,
        info: <InfoIcon weight="fill" aria-hidden="true" />,
        warning: <WarningCircleIcon weight="fill" aria-hidden="true" />,
        error: <XCircleIcon weight="fill" aria-hidden="true" />,
      }}
      toastOptions={{
        classNames: {
          toast: "app-toast",
          title: "app-toast-title",
          description: "app-toast-description",
          closeButton: "app-toast-close",
          success: "app-toast-success",
          error: "app-toast-error",
          warning: "app-toast-warning",
          info: "app-toast-info",
        },
      }}
    />
  );
}
