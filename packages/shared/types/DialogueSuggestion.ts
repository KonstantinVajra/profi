/**
 * DialogueSuggestion
 *
 * Dialogue copilot output.
 * Given a client message, the AI returns this structure to help
 * the freelancer respond appropriately at the right funnel stage.
 *
 * Mirror of backend app/schemas/dialogue.py :: DialogueSuggestion
 */

export type FunnelStage =
  | "new_lead"
  | "replied"
  | "opened"
  | "engaged"
  | "qualified"
  | "booked"
  | "lost";

export interface DialogueSuggestion {
  /** Plain-language summary of what the client wants. */
  intent: string;
  /** Current stage in the conversion funnel. */
  funnel_stage: FunnelStage;
  /** Always exactly 3 reply options. */
  suggestions: [string, string, string];
  /** The single best follow-up question to move the deal forward. */
  next_best_question: string;
}
