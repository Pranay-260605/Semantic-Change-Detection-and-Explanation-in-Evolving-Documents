import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function titleForChange(type: string): string {
  const labels: Record<string, string> = {
    UNCHANGED: "Unchanged",
    ADDITION: "Addition",
    DELETION: "Deletion",
    MODIFICATION: "Modification",
    NUMERICAL_CHANGE: "Numerical change",
    TEMPORAL_CHANGE: "Temporal change",
    ENTITY_CHANGE: "Entity change",
    CONTRADICTION: "Contradiction",
    REFINEMENT: "Refinement",
  };
  return labels[type] ?? "Change";
}

export function changeTone(type: string): string {
  const tones: Record<string, string> = {
    ADDITION: "tone-addition",
    DELETION: "tone-deletion",
    MODIFICATION: "tone-modification",
    NUMERICAL_CHANGE: "tone-numerical",
    TEMPORAL_CHANGE: "tone-temporal",
    ENTITY_CHANGE: "tone-entity",
    CONTRADICTION: "tone-contradiction",
    REFINEMENT: "tone-refinement",
    UNCHANGED: "tone-unchanged",
  };
  return tones[type] ?? "tone-modification";
}
