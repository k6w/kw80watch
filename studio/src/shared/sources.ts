export interface NumericSource {
  id: number;
  label: string;
  short: string;
  unit?: string;
  hasSuffix?: boolean;
  min: number;
  max: number;
}

export interface PictureSetType {
  id: number;
  label: string;
  short: string;
  states: number;
  stateLabels?: string[];
}

export interface RotationSource {
  id: number;
  label: string;
  short: string;
  range: number;
  // function to compute angle (degrees) from simulated data
  toAngle: (data: SimData) => number;
}

export interface SimData {
  hour: number;       // 0-23
  minute: number;     // 0-59
  second: number;     // 0-59
  steps: number;
  heartRate: number;
  calories: number;
  temperature: number;
  battery: number;
  dayOfMonth: number; // 1-31
  month: number;      // 1-12
  weekday: number;    // 0=Sunday
  weather: number;    // 0-23
}

export const NUMERIC_SOURCES: NumericSource[] = [
  { id: 0,  label: "Steps",         short: "steps",  min: 0, max: 50000 },
  { id: 1,  label: "Calories",      short: "kcal",   min: 0, max: 2000 },
  { id: 2,  label: "Heart Rate",    short: "bpm",    min: 40, max: 200 },
  { id: 4,  label: "Temperature",   short: "temp",   min: -20, max: 50, hasSuffix: true },
  { id: 9,  label: "Battery",       short: "bat",    min: 0, max: 100, hasSuffix: true },
  { id: 12, label: "Hour",          short: "hr",     min: 0, max: 23 },
  { id: 13, label: "Minute",        short: "min",    min: 0, max: 59 },
  { id: 14, label: "Second",        short: "sec",    min: 0, max: 59 },
  { id: 17, label: "Day of Month",  short: "date",   min: 1, max: 31 },
  { id: 51, label: "Month Number",  short: "mon",    min: 1, max: 12 },
];

export const PICTURE_SET_TYPES: PictureSetType[] = [
  { id: 50,  label: "AM / PM",           short: "ampm",    states: 3,  stateLabels: ["AM", "PM", "24H"] },
  { id: 51,  label: "Month Name",         short: "month",   states: 12, stateLabels: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"] },
  { id: 52,  label: "Weekday",            short: "weekday", states: 7,  stateLabels: ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"] },
  { id: 54,  label: "Battery Icon",       short: "baticon", states: 11 },
  { id: 59,  label: "Hour Tens",          short: "hr10",    states: 10, stateLabels: ["0","1","2","3","4","5","6","7","8","9"] },
  { id: 60,  label: "Hour Units",         short: "hr1",     states: 10, stateLabels: ["0","1","2","3","4","5","6","7","8","9"] },
  { id: 61,  label: "Minute Tens",        short: "min10",   states: 10, stateLabels: ["0","1","2","3","4","5","6","7","8","9"] },
  { id: 62,  label: "Minute Units",       short: "min1",    states: 10, stateLabels: ["0","1","2","3","4","5","6","7","8","9"] },
  { id: 65,  label: "Steps Digit 1",      short: "s1",      states: 10 },
  { id: 66,  label: "Steps Digit 2",      short: "s2",      states: 10 },
  { id: 67,  label: "Steps Digit 3",      short: "s3",      states: 10 },
  { id: 68,  label: "Steps Digit 4",      short: "s4",      states: 10 },
  { id: 69,  label: "Steps Digit 5",      short: "s5",      states: 10 },
  { id: 70,  label: "Day Tens",           short: "d10",     states: 4 },
  { id: 71,  label: "Day Units",          short: "d1",      states: 10 },
  { id: 73,  label: "Two-State Indicator", short: "2st",    states: 2 },
  { id: 181, label: "Bluetooth Status",   short: "bt",      states: 2,  stateLabels: ["Disconnected", "Connected"] },
  { id: 212, label: "Calories Gauge",     short: "kcal-g",  states: 11 },
  { id: 219, label: "Heart Rate Gauge",   short: "hr-g",    states: 11 },
  { id: 239, label: "Steps Gauge",        short: "step-g",  states: 11 },
  { id: 248, label: "Weather Condition",  short: "wx",      states: 24, stateLabels: [
    "Unknown","Sunny","Cloudy","Overcast","Light Rain","Moderate Rain",
    "Heavy Rain","Storm","Drizzle","Sleet","Snow","Heavy Snow",
    "Foggy","Haze","Sandstorm","Showers","Hail","Thunderstorm",
    "Wind","Hot","Cold","UV High","Air Poor","Air Good",
  ] },
];

export const ROTATION_SOURCES: RotationSource[] = [
  { id: 150, label: "Hour Hand (12h)",   short: "hour",   range: 360, toAngle: (d) => ((d.hour % 12) + d.minute / 60) * 30 },
  { id: 151, label: "Hour Hand (24h)",   short: "hour24", range: 360, toAngle: (d) => (d.hour + d.minute / 60) * 15 },
  { id: 153, label: "Minute Hand",       short: "min",    range: 360, toAngle: (d) => (d.minute + d.second / 60) * 6 },
  { id: 154, label: "Second Hand",       short: "sec",    range: 360, toAngle: (d) => d.second * 6 },
  { id: 155, label: "Day of Month",      short: "date",   range: 360, toAngle: (d) => ((d.dayOfMonth - 1) / 31) * 360 },
  { id: 156, label: "Weekday",           short: "wd",     range: 360, toAngle: (d) => (d.weekday / 7) * 360 },
  { id: 157, label: "Heart Rate",        short: "hr-rot", range: 360, toAngle: (d) => ((d.heartRate - 40) / 160) * 360 },
  { id: 158, label: "Calories",          short: "cal-r",  range: 360, toAngle: (d) => (d.calories / 2000) * 360 },
  { id: 161, label: "Steps",             short: "step-r", range: 360, toAngle: (d) => (d.steps / 50000) * 360 },
  { id: 163, label: "Battery",           short: "bat-r",  range: 360, toAngle: (d) => (d.battery / 100) * 360 },
  { id: 255, label: "Static (no rotation)", short: "static", range: 0, toAngle: () => 0 },
];

export const WEEKDAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
export const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export function getNumericSource(id: number) { return NUMERIC_SOURCES.find((s) => s.id === id); }
export function getPictureSetType(id: number) { return PICTURE_SET_TYPES.find((t) => t.id === id); }
export function getRotationSource(id: number) { return ROTATION_SOURCES.find((s) => s.id === id); }
