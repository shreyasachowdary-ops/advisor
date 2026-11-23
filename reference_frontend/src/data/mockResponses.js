import { quickTopics } from "./quickTopics.js";

export { quickTopics };

export const parentExamples = [
  "My 4-year-old refuses to get ready for preschool. What can we try this week?",
  "My child finds it difficult to share toys. What can I do?",
  "My child has been very distressed for several weeks and it is affecting preschool.",
  "What should I ask the teacher if my child avoids group activities?",
];

export const teacherExamples = [
  "A 3-year-old often pushes during group play. What strategies can I try?",
  "Suggest five days of 15-minute activities to build turn-taking for 4-year-olds.",
  "The student is being bullied.",
  "How can I communicate a classroom concern to parents without blame?",
];

const commonSources = {
  cdc: {
    publisher: "CDC",
    title: "Positive Parenting Tips",
    description: "Age-based guidance for supporting young children's development.",
    url: "https://www.cdc.gov/child-development/positive-parenting-tips/index.html",
    chunk_id: "cdc-positive-parenting",
  },
  pbis: {
    publisher: "PBIS",
    title: "Positive Behaviour Support Materials",
    description: "Classroom strategies that emphasize prevention, teaching, and reinforcement.",
    url: "https://www.pbis.org/resource-type/materials",
    chunk_id: "pbis-materials",
  },
  familyEngagement: {
    publisher: "U.S. Department of Education",
    title: "Family Partnership and Engagement",
    description: "Resources for respectful family-school communication.",
    url: "https://www.ed.gov/birth-grade-12-education/resources-families/family-partnership-and-engagement",
    chunk_id: "ed-family-engagement",
  },
};

export function getMockResponse(payload) {
  const message = payload.message.toLowerCase();

  if (message.includes("bullied") || message.includes("bullying")) {
    return urgentResponse();
  }

  if (message.includes("distressed") || message.includes("several weeks")) {
    return referralResponse();
  }

  if (message.includes("five days") || message.includes("5 days") || message.includes("turn-taking")) {
    return activityPlanResponse();
  }

  if (message.includes("pushing") || message.includes("pushes")) {
    return teacherPushingResponse();
  }

  if (message.includes("no sources")) {
    return noSourcesResponse();
  }

  return parentMorningResponse(payload);
}

function parentMorningResponse(payload) {
  return {
    answer:
      "Preschool mornings often become difficult because the child is moving from comfort and play into a less preferred transition. A short, predictable routine can reduce negotiation and help the child feel more capable.",
    risk_level: "normal",
    requires_human_review: false,
    sections: [
      {
        title: "What may help this week",
        items: [
          "Use the same three-step sequence each morning: bathroom, clothes, breakfast bag.",
          "Offer two acceptable choices, such as the red socks or the blue socks.",
          "Use a simple picture routine or checklist the child can move through.",
          "Praise the exact cooperative action: You put your shoes by the door when I asked.",
        ],
      },
      {
        title: "What to observe",
        body:
          "Notice whether the difficulty is strongest during waking, dressing, leaving preferred toys, or the final goodbye. That pattern helps adults adjust the routine instead of treating the whole morning as one problem.",
      },
      {
        title: "Discuss with the other adult",
        body:
          "If preschool transitions are also hard, compare what works at home and school. A shared phrase or visual cue can make the routine feel familiar in both places.",
      },
    ],
    sources: [commonSources.cdc, commonSources.familyEngagement],
    suggested_follow_up: `What part of the morning is hardest for this ${payload.age_band.replace("_", " ")} child?`,
  };
}

function teacherPushingResponse() {
  return {
    answer:
      "Pushing during group play is best handled as a skill-building need, not a character flaw. The goal is to prevent crowded moments, teach replacement language, and reinforce safe participation.",
    risk_level: "normal",
    requires_human_review: false,
    sections: [
      {
        title: "Classroom strategies",
        items: [
          "Reduce crowding by limiting the number of children in high-interest centers.",
          "Teach and model one replacement phrase, such as My turn next or I need space.",
          "Stand close during predictable high-friction moments and prompt before pushing happens.",
          "Notice safe play out loud so the child knows what to repeat.",
        ],
      },
      {
        title: "Observable patterns",
        body:
          "Track when pushing happens: entry into play, waiting for materials, cleanup, or loud group moments. Keep notes factual and brief, without labels or diagnosis.",
      },
      {
        title: "Family communication",
        body:
          "Share the skill being taught and invite consistency: We are practicing asking for space and waiting for a turn. What words do you use at home?",
      },
    ],
    sources: [commonSources.pbis, commonSources.familyEngagement],
    suggested_follow_up: "When does the pushing most often happen during the day?",
  };
}

function activityPlanResponse() {
  return {
    answer:
      "Here is a short activity plan designed for a classroom or small-group setting. Keep the tone playful and stop while children are still successful.",
    risk_level: "normal",
    requires_human_review: false,
    activity_plan: {
      title: "5-Day Turn-Taking Plan",
      age: "4 years",
      time: "15 minutes/day",
      setting: "Classroom",
      days: [
        {
          day: "Day 1",
          title: "Passing the Toy",
          setup: "Use one appealing toy and seat children in a small circle.",
          adultLanguage: "My turn, your turn, waiting hands.",
          steps: ["Show the turn phrase.", "Pass the toy around the circle.", "Celebrate waiting and passing."],
          observe: "Who can wait with a visual or verbal cue?",
        },
        {
          day: "Day 2",
          title: "Build Together",
          setup: "Give each child a small set of blocks.",
          adultLanguage: "Add one, then pass.",
          steps: ["Start a shared tower.", "Each child adds one block.", "Pause to name patient waiting."],
          observe: "Which children need a shorter wait time?",
        },
        {
          day: "Day 3",
          title: "Turn Cards",
          setup: "Use two cards: My turn and Waiting.",
          adultLanguage: "The card shows what your body is doing.",
          steps: ["Practice switching cards.", "Pair cards with a brief game.", "Let children hand over the turn card."],
          observe: "Does the visual reduce adult reminders?",
        },
        {
          day: "Day 4",
          title: "Partner Puzzle",
          setup: "Choose a puzzle with large pieces.",
          adultLanguage: "Ask, choose, place, pass.",
          steps: ["Pair children.", "Each child places one piece.", "Prompt asking before reaching."],
          observe: "Who asks independently before taking a piece?",
        },
        {
          day: "Day 5",
          title: "Choice Game",
          setup: "Offer two familiar turn-taking games.",
          adultLanguage: "We can choose a game and still keep turns fair.",
          steps: ["Children vote between two games.", "Review the turn rule.", "Play and end with one success noticed for each child."],
          observe: "Which routines are ready to use during free play?",
        },
      ],
    },
    sources: [commonSources.pbis],
    suggested_follow_up: "Would you like this adapted for home, classroom, or a mixed-age group?",
  };
}

function urgentResponse() {
  return {
    answer: "",
    risk_level: "urgent",
    requires_human_review: true,
    sources: [],
    suggested_follow_up: "",
  };
}

function referralResponse() {
  return {
    answer:
      "Persistent distress that affects daily preschool participation may benefit from coordinated adult support. Keep observations factual, gentle, and focused on what helps the child feel safe and engaged.",
    risk_level: "refer_to_support",
    requires_human_review: true,
    sections: [
      {
        title: "Next supportive steps",
        items: [
          "Share brief observations with the teacher or school support professional.",
          "Look for patterns around sleep, separation, transitions, peers, or sensory load.",
          "Agree on one calming routine to try consistently for a week.",
        ],
      },
    ],
    sources: [commonSources.cdc],
    suggested_follow_up: "What changes have adults noticed at home and at preschool?",
  };
}

function noSourcesResponse() {
  return {
    answer:
      "I can offer general educational guidance, but this mock response did not receive any retrieved source material from the backend.",
    risk_level: "normal",
    requires_human_review: false,
    sections: [
      {
        title: "Frontend behavior",
        body:
          "The interface should say that no specific sources were returned rather than inventing citations.",
      },
    ],
    sources: [],
    suggested_follow_up: "Would you like to try the same question with sources enabled later?",
  };
}
