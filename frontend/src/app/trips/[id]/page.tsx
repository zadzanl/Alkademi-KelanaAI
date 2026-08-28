import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTrip } from "../../../services/tripService.ts";
import { parseTripId } from "../../../lib/safety.ts";
import { TripDetailView } from "../../../components/TripDetailView.tsx";

export const dynamic = "force-dynamic";

interface TripDetailPageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({
  params,
}: TripDetailPageProps): Promise<Metadata> {
  try {
    const { id: rawId } = await params;
    const tripId = parseTripId(rawId);
    if (tripId === null) {
      return { title: "Trip Not Found | KelanaAI" };
    }

    const trip = await getTrip(tripId);
    if (!trip) {
      return { title: "Trip Not Found | KelanaAI" };
    }

    return {
      title: `${trip.destination}, ${trip.country} (${trip.days} Days) | KelanaAI`,
      description: `Trip itinerary for ${trip.destination}, ${trip.country}. Budget: ${trip.currency} ${Number(trip.budget).toLocaleString()}. Category: ${trip.category}.`,
    };
  } catch {
    return { title: "Trip Details | KelanaAI" };
  }
}

export default async function TripDetailPage({ params }: TripDetailPageProps) {
  const { id: rawId } = await params;
  const tripId = parseTripId(rawId);

  if (tripId === null) {
    notFound();
  }

  const trip = await getTrip(tripId);

  if (!trip) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      <main className="mx-auto max-w-6xl px-5 py-12 sm:px-8">
        <TripDetailView
          trip={trip}
          headingLevel="h1"
          showBackLink={true}
          backHref="/trips"
          backLabel="Back to My Trips"
        />
      </main>
    </div>
  );
}

