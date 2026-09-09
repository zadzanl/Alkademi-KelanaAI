type VineOrientation = "top-right" | "bottom-left";

type FlowerProps = {
	className: string;
};

const PETAL_ROTATIONS = [0, 72, 144, 216, 288] as const;

function Vine({ orientation }: { orientation: VineOrientation }) {
	const mirrorTransform = orientation === "top-right"
		? "translate(240 0) scale(-1 1)"
		: "translate(0 320) scale(1 -1)";

	return (
		<svg
			viewBox="0 0 240 320"
			aria-hidden="true"
			focusable="false"
			role="presentation"
		>
			<g transform={mirrorTransform}>
				<path className="nature-vine__stem" d="M238 0C208 46 202 91 185 132c-22 53-62 76-94 113-22 26-35 49-48 75" />
				<path d="M205 69c-34-21-57-17-69 5 23 20 47 19 69-5Z" fill="currentColor" stroke="none" />
				<path d="M175 136c-38-14-59-5-65 20 29 15 51 8 65-20Z" fill="currentColor" stroke="none" />
				<path d="M124 198c-31-2-47 12-43 35 26 6 41-5 43-35Z" fill="currentColor" stroke="none" />
				<path d="M88 255c-22 7-30 22-19 37 19-1 26-13 19-37Z" fill="currentColor" stroke="none" />
			</g>
		</svg>
	);
}

function Flower({ className }: FlowerProps) {
	return (
		<svg className={className} viewBox="0 0 32 32" aria-hidden="true" focusable="false" role="presentation">
			<g fill="none" stroke="currentColor" strokeWidth={1.5}>
				{PETAL_ROTATIONS.map((rotation) => (
					<ellipse key={rotation} cx="16" cy="8" rx="4" ry="7" transform={`rotate(${rotation} 16 16)`} />
				))}
			</g>
			<circle className="nature-flower__center" cx="16" cy="16" r="3" />
		</svg>
	);
}

function PaperAirplanePath() {
	return (
		<svg viewBox="0 0 224 96" aria-hidden="true" focusable="false" role="presentation">
			<path className="nature-motif__dash" d="M4 88C60 80 104 58 142 40S198 16 214 12" />
			<g transform="translate(214 12) rotate(-18)">
				<path className="nature-motif__accent" d="M0 0-20 6-8 2-14 16-4 7Z" />
				<path d="m-8 2 4 5" />
				<path d="m-20 6 12-4" />
			</g>
		</svg>
	);
}

function CompassRose() {
	return (
		<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false" role="presentation">
			<circle cx="32" cy="32" r="28" />
			<path d="M32 1v7M32 56v7M1 32h7M56 32h7" />
			<path d="m10.1 10.1 5 5M48.9 48.9l5 5M53.9 10.1l-5 5M15.1 48.9l-5 5" />
			<path className="nature-motif__accent" d="M32 8 36 32 32 32Z" />
			<path d="m32 56-4-24 4 0Z" />
			<path d="M32 8 36 32 32 56 28 32Z" />
			<circle cx="32" cy="32" r="2" />
		</svg>
	);
}

function LineGlobe() {
	return (
		<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false" role="presentation">
			<circle cx="32" cy="32" r="28" />
			<ellipse cx="32" cy="32" rx="12" ry="28" />
			<ellipse cx="32" cy="32" rx="21" ry="28" />
			<ellipse className="nature-motif__accent" cx="32" cy="32" rx="28" ry="9" />
		</svg>
	);
}

function RoutePin() {
	return (
		<svg viewBox="0 0 96 64" aria-hidden="true" focusable="false" role="presentation">
			<path className="nature-motif__dash" d="M4 56C24 48 22 30 44 27S74 18 79 11" />
			<path d="M79 6C74.6 6 71 9.4 71 14c0 6.1 8 14 8 14s8-7.9 8-14c0-4.6-3.6-8-8-8Z" />
			<circle className="nature-motif__accent" cx="79" cy="14" r="2" fill="rgb(13 118 110 / 50%)" />
		</svg>
	);
}

export function NatureBackground() {
	return (
		<div className="nature-background" aria-hidden="true">
			<div className="nature-background__aura" />
			<div className="nature-vine nature-vine--top-right">
				<Vine orientation="top-right" />
			</div>
			<div className="nature-vine nature-vine--bottom-left">
				<Vine orientation="bottom-left" />
			</div>
			<div className="nature-motif nature-motif--plane">
				<PaperAirplanePath />
			</div>
			<div className="nature-motif nature-motif--compass">
				<CompassRose />
			</div>
			<div className="nature-motif nature-motif--globe">
				<LineGlobe />
			</div>
			<div className="nature-motif nature-motif--route">
				<RoutePin />
			</div>
			<div className="nature-flowers">
				<Flower className="nature-flower nature-flower--one" />
				<Flower className="nature-flower nature-flower--two" />
			</div>
		</div>
	);
}