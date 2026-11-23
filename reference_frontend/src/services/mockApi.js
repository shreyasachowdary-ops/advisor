import { getMockResponse } from "../data/mockResponses.js";

const RESPONSE_DELAY_MS = 700;

export async function mockSendChatMessage(payload) {
  await wait(RESPONSE_DELAY_MS);

  if (payload.message.toLowerCase().includes("force error")) {
    throw new Error("Mock request failed");
  }

  return getMockResponse(payload);
}

export async function mockSubmitFeedback(messageId, feedbackType) {
  await wait(180);
  return {
    ok: true,
    messageId,
    feedbackType,
  };
}

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
