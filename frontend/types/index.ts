export type DinnerIntent = {
  group_size?: number | null;
  cuisines: string[];
  price_level: number | null;
  location: string | null;
  radius: number | null;
  vibe: string | null;
  dietary_preferences?: string[];
};

export type Participant = {
  id: string;
  nickname: string;
  is_host: boolean;
};

export type Progress = {
  finished: number;
  total: number;
};

export type DinnerSession = {
  id: string;
  room_code: string;
  description: string;
  status: "lobby" | "active" | "completed";
  host_participant_id: string;
  created_at: string;
  updated_at: string;
  participants: Participant[];
  restaurant_count: number;
  progress: Progress;
  participant?: Participant;
  intent?: DinnerIntent;
};

export type Restaurant = {
  id: string;
  name: string;
  description: string | null;
  cuisine: string | null;
  categories?: string[];
  price: number | null;
  rating: number | null;
  latitude: number | null;
  longitude: number | null;
  address: string | null;
  phone?: string | null;
  website?: string | null;
  image_url: string | null;
  source: string;
  position: number;
  my_decision: "like" | "pass" | "super_like" | "veto" | null;
};

export type RestaurantResult = {
  restaurant_id: string;
  name: string;
  description: string | null;
  cuisine: string | null;
  price: number | null;
  rating: number | null;
  address: string | null;
  latitude?: number | null;
  longitude?: number | null;
  phone?: string | null;
  website?: string | null;
  image_url: string | null;
  likes: number;
  super_likes?: number;
  passes?: number;
  vetoes?: number;
  total_participants: number;
  eliminated?: boolean;
  compatibility: number;
  compatibility_percent: number;
  explanation: string;
  positives?: number;
  satisfaction_percent?: number;
  elimination_reason?: "veto" | "budget" | "distance" | "diet" | null;
  fairness?: { least_satisfied_percent: number; average_satisfaction_percent: number } | null;
  rank?: number;
  highlight?: "best_balance" | "strongest_support" | "higher_satisfaction" | null;
};

export type Results = {
  room_code: string;
  status: string;
  total_participants: number;
  top_match: RestaurantResult | null;
  alternatives: RestaurantResult[];
};

export type SwipeResult = {
  id: string;
  restaurant_id: string;
  decision: "like" | "pass" | "super_like" | "veto";
  progress: Progress;
  all_completed: boolean;
  super_like_remaining?: boolean;
  veto_remaining?: boolean;
};

export type LiveEvent = {
  type: string;
  status?: DinnerSession["status"];
  finished?: number;
  total?: number;
  participant?: { id: string; nickname: string };
  participant_count?: number;
  restaurant_count?: number;
  top_match?: {
    name: string;
    compatibility_percent: number;
    likes: number;
    total_participants: number;
  } | null;
  detail?: string;
};

export type Identity = {
  participantId: string;
  nickname: string;
};
