export type TripCategory = "Backpacker" | "Standard" | "Luxury" | string;

export type FormValues = {
  destination: string;
  country: string;
  days: string;
  budget: string;
  currency: "IDR" | "USD";
  travel_month: string;
};

export type TripRequest = Omit<FormValues, "days" | "budget"> & {
  days: number;
  budget: number;
};

export type TripResponse = {
  id: number;
  destination: string;
  country: string;
  days: number;
  budget: number;
  currency: string;
  travel_month: string;
  daily_budget: number;
  travel_season: string;
  category: TripCategory;
  recommended_places: string[];
  recommended_transportation: string;
  created_at: string;
  ai_recommendation: string | null;
};

export type TripListResponse = {
  items: TripResponse[];
  total: number;
  page: number;
  page_size: number;
};

export type ActionState =
  | { ok: true; trip: TripResponse; submitted: FormValues }
  | {
      ok: false;
      kind: "validation" | "timeout" | "network" | "upstream" | "malformed" | "unauthorized";
      message: string;
      fieldErrors?: Partial<Record<keyof FormValues, string>>;
      submitted: FormValues;
    };

export const initialForm: FormValues = {
  destination: "",
  country: "",
  days: "5",
  budget: "1500",
  currency: "USD",
  travel_month: "December",
};

export const months = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

