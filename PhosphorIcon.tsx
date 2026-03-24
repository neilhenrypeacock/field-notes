import { View } from 'react-native'
import Svg, { Path, Circle, Line, Polyline, Rect, Ellipse, Polygon, Defs, RadialGradient, Stop } from 'react-native-svg'

type Props = {
  name: keyof typeof ICONS
  size?: number
  color: string
  accessibilityLabel?: string
}

export function PhosphorIcon({ name, size = 20, color, accessibilityLabel }: Props) {
  const render = ICONS[name]
  if (!render) return null
  const svg = render(size, color)
  if (accessibilityLabel) {
    return <View accessible accessibilityLabel={accessibilityLabel}>{svg}</View>
  }
  return svg
}

// All icons from Phosphor Light set (viewBox 0 0 256 256, strokeWidth 12)
const ICONS = {
  'chat-circle': (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Path
        d="M79.93,211.11a96,96,0,1,0-35-35h0L32.42,213.46a8,8,0,0,0,10.12,10.12l37.39-12.47Z"
        stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round"
      />
    </Svg>
  ),
  user: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Circle cx={128} cy={96} r={64} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path
        d="M32,216c19.37-33.47,54.55-56,96-56s76.63,22.53,96,56"
        stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round"
      />
    </Svg>
  ),
  microphone: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Rect x={88} y={24} width={80} height={144} rx={40} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={128} y1={200} x2={128} y2={240} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M200,128a72,72,0,0,1-144,0" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  'circle-half': (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Line x1={192} y1={56.45} x2={192} y2={199.55} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={160} y1={37.47} x2={160} y2={218.53} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Circle cx={128} cy={128} r={96} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={128} y1={32} x2={128} y2={224} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  bell: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Path d="M96,192a32,32,0,0,0,64,0" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path
        d="M56,104a72,72,0,0,1,144,0c0,35.82,8.3,64.6,14.9,76A8,8,0,0,1,208,192H48a8,8,0,0,1-6.88-12C47.71,168.6,56,139.81,56,104Z"
        stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round"
      />
    </Svg>
  ),
  'credit-card': (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Rect x={24} y={56} width={208} height={144} rx={8} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={168} y1={168} x2={200} y2={168} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={120} y1={168} x2={136} y2={168} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={24} y1={96} x2={232} y2={96} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  info: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Path d="M120,120a8,8,0,0,1,8,8v40a8,8,0,0,0,8,8" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Circle cx={124} cy={84} r={10} fill={color} />
      <Circle cx={128} cy={128} r={96} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  database: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Ellipse cx={128} cy={80} rx={88} ry={48} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M40,80v48c0,26.51,39.4,48,88,48s88-21.49,88-48V80" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M40,128v48c0,26.51,39.4,48,88,48s88-21.49,88-48V128" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  'caret-right': (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Polyline points="96,48 176,128 96,208" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  'envelope-simple': (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Path d="M32,56H224a0,0,0,0,1,0,0V192a8,8,0,0,1-8,8H40a8,8,0,0,1-8-8V56A0,0,0,0,1,32,56Z" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Polyline points="224,56 128,144 32,56" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  lock: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Rect x={40} y={88} width={176} height={128} rx={8} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Circle cx={128} cy={152} r={10} fill={color} />
      <Path d="M88,88V56a40,40,0,0,1,80,0V88" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  headphones: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Path
        d="M224,128H192a16,16,0,0,0-16,16v40a16,16,0,0,0,16,16h16a16,16,0,0,0,16-16V128a96,96,0,1,0-192,0v56a16,16,0,0,0,16,16H64a16,16,0,0,0,16-16V144a16,16,0,0,0-16-16H32"
        stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round"
      />
    </Svg>
  ),
  'chat-circle-dots': (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Circle cx={128} cy={128} r={10} fill={color} />
      <Circle cx={84} cy={128} r={10} fill={color} />
      <Circle cx={172} cy={128} r={10} fill={color} />
      <Path
        d="M79.93,211.11a96,96,0,1,0-35-35h0L32.42,213.46a8,8,0,0,0,10.12,10.12l37.39-12.47Z"
        stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round"
      />
    </Svg>
  ),
  'skip-forward': (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Line x1={200} y1={40} x2={200} y2={216} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path
        d="M56,47.88V208.12a8,8,0,0,0,12.19,6.65L196.3,134.65a7.83,7.83,0,0,0,0-13.3L68.19,41.23A8,8,0,0,0,56,47.88Z"
        stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round"
      />
    </Svg>
  ),
  compass: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Circle cx={128} cy={128} r={96} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Polygon
        points="176,80 112,112 80,176 144,144 176,80"
        stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" fill="none"
      />
    </Svg>
  ),
  'pencil-simple': (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Path
        d="M92.69,216H48a8,8,0,0,1-8-8V163.31a8,8,0,0,1,2.34-5.65L165.66,34.34a8,8,0,0,1,11.31,0L221.66,79a8,8,0,0,1,0,11.31L98.34,213.66A8,8,0,0,1,92.69,216Z"
        stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round"
      />
      <Line x1={136} y1={64} x2={192} y2={120} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  'book-open': (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Path
        d="M128,88a32,32,0,0,1,32-32h72V200H160a32,32,0,0,0-32,32"
        stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round"
      />
      <Path
        d="M24,200H96a32,32,0,0,1,32,32V88A32,32,0,0,0,96,56H24Z"
        stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round"
      />
    </Svg>
  ),
  handshake: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Polyline points="200 152 160 192 96 176 40 136" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Polyline points="72.68 70.63 128 56 183.32 70.63" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M34.37,60.42,8.85,111.48a8,8,0,0,0,3.57,10.73L40,136,72.68,70.63,45.11,56.85A8,8,0,0,0,34.37,60.42Z" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M216,136l27.58-13.79a8,8,0,0,0,3.57-10.73L221.63,60.42a8,8,0,0,0-10.74-3.57L183.32,70.63Z" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M184,72H144L98.34,116.29a8,8,0,0,0,1.38,12.42C117.23,139.9,141,139.13,160,120l40,32,16-16" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Polyline points="124.06 216 82.34 205.57 56 186.75" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  'pen-nib': (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Path d="M40,216l139.45-23.24a8,8,0,0,0,6.17-5.08L208,128,128,48,68.32,70.38a8,8,0,0,0-5.08,6.17Z" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M208,128l29.66-29.66a8,8,0,0,0,0-11.31L169,18.34a8,8,0,0,0-11.31,0L128,48" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Circle cx={124} cy={132} r={20} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={40.01} y1={216} x2={109.86} y2={146.14} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  lightning: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Polygon points="160,16 144,96 208,120 96,240 112,160 48,136 160,16" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </Svg>
  ),
  sparkle: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Path d="M84.27,171.73l-55.09-20.3a7.92,7.92,0,0,1,0-14.86l55.09-20.3,20.3-55.09a7.92,7.92,0,0,1,14.86,0l20.3,55.09,55.09,20.3a7.92,7.92,0,0,1,0,14.86l-55.09,20.3-20.3,55.09a7.92,7.92,0,0,1-14.86,0Z" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={176} y1={16} x2={176} y2={64} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={224} y1={72} x2={224} y2={104} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={152} y1={40} x2={200} y2={40} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={208} y1={88} x2={240} y2={88} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  'magnifying-glass': (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Circle cx={112} cy={112} r={80} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={168.57} y1={168.57} x2={224} y2={224} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  gauge: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Path d="M24,176V153.13C24,95.65,70.15,48.2,127.63,48A104,104,0,0,1,232,152v24a8,8,0,0,1-8,8H32A8,8,0,0,1,24,176Z" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={128} y1={48} x2={128} y2={80} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={104} y1={184} x2={168} y2={96} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={200} y1={136} x2={230.78} y2={136} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={25.39} y1={136} x2={56} y2={136} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  play: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Path
        d="M72,39.88V216.12a8,8,0,0,0,12.15,6.69l144.08-88.12a7.82,7.82,0,0,0,0-13.38L84.15,33.19A8,8,0,0,0,72,39.88Z"
        stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round"
      />
    </Svg>
  ),
  flag: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Line x1={48} y1={224} x2={48} y2={56} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M48,176c64-55.43,112,55.43,176,0V56C160,111.43,112,.57,48,56" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
  trash: (size: number, color: string) => (
    <Svg width={size} height={size} viewBox="0 0 256 256" fill="none">
      <Line x1={216} y1={56} x2={40} y2={56} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={104} y1={104} x2={104} y2={168} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Line x1={152} y1={104} x2={152} y2={168} stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M200,56V208a8,8,0,0,1-8,8H64a8,8,0,0,1-8-8V56" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
      <Path d="M168,56V40a16,16,0,0,0-16-16H104A16,16,0,0,0,88,40V56" stroke={color} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ),
} as const
