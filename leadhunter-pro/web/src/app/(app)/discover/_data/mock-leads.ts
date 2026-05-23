/**
 * Mock dataset estilo "asesoría fiscal en Sevilla".
 * Mantener estable hasta que el backend Python real esté detrás de FastAPI:
 * estos leads son los que devuelve hoy el comando
 *   python main.py discover --geo Sevilla --sector "asesoría fiscal"
 * tras los fixes de la auditoría (commit 9cb32cb).
 */

export type Grade = "A" | "B" | "C" | "D";

export type SourceKey =
  | "BORME"
  | "OSM"
  | "Cartociudad"
  | "PLACSP"
  | "AEPD"
  | "DDG"
  | "WebContact";

export interface DecisionMaker {
  name: string;
  role: string;
  email?: string;
}

export interface Lead {
  id: string;
  razonSocial: string;
  nif?: string;
  city: string;
  province: string;
  score: number;
  grade: Grade;
  decisor?: string;
  decisorRole?: string;
  email?: string;
  emailConfidence?: "high" | "medium" | "low";
  phone?: string;
  domain?: string;
  cnae?: string;
  sources: readonly SourceKey[];
  compliance: {
    dpoRegistered: boolean | null;
    note?: string;
  };
  publicSector: {
    contracts: number;
    subsidies: number;
  };
  decisionMakers: readonly DecisionMaker[];
  webNote?: string;
}

export const MOCK_LEADS: readonly Lead[] = [
  {
    id: "asesoria-camen",
    razonSocial: "Asesoría Camen S.L.",
    nif: "B41234567",
    city: "Sevilla",
    province: "Sevilla",
    score: 65,
    grade: "B",
    decisor: "Manuel Campo",
    decisorRole: "Socio / Propietario",
    email: "manuel.campo@asesoriacamen.es",
    emailConfidence: "high",
    phone: "+34 955 67 51 68",
    domain: "asesoriacamen.es",
    cnae: "6920",
    sources: ["BORME", "OSM", "Cartociudad", "WebContact"],
    compliance: { dpoRegistered: false },
    publicSector: { contracts: 0, subsidies: 0 },
    decisionMakers: [
      { name: "Manuel Campo", role: "Socio / Propietario", email: "manuel.campo@asesoriacamen.es" },
      { name: "Tomás Campo", role: "Socio / Propietario", email: "tomas.campo@asesoriacamen.es" },
      { name: "Pablo Campo", role: "Área Fiscal Contable", email: "pablo.campo@asesoriacamen.es" },
      { name: "Jesús García", role: "Área Fiscal Contable" },
      { name: "Laura Rodríguez", role: "Área Contable Laboral" },
    ],
  },
  {
    id: "segean-asesores",
    razonSocial: "Segean Asesores",
    nif: "B41782341",
    city: "Sevilla",
    province: "Sevilla",
    score: 52,
    grade: "B",
    decisor: "Sergio Eanes",
    decisorRole: "Gerente",
    email: "info@segeanasesores.es",
    emailConfidence: "medium",
    phone: "+34 954 32 18 90",
    domain: "segeanasesores.es",
    cnae: "6920",
    sources: ["BORME", "OSM", "WebContact"],
    compliance: { dpoRegistered: false },
    publicSector: { contracts: 0, subsidies: 1 },
    decisionMakers: [
      { name: "Sergio Eanes", role: "Gerente", email: "sergio@segeanasesores.es" },
    ],
  },
  {
    id: "lm-asesores",
    razonSocial: "L&M Asesores",
    nif: "B41056789",
    city: "Mairena del Aljarafe",
    province: "Sevilla",
    score: 48,
    grade: "B",
    decisor: "Luisa Marín",
    decisorRole: "Administradora única",
    email: "luisa.marin@lmasesores.com",
    emailConfidence: "high",
    phone: "+34 955 12 88 41",
    domain: "lmasesores.com",
    cnae: "6920",
    sources: ["BORME", "OSM", "WebContact"],
    compliance: { dpoRegistered: true },
    publicSector: { contracts: 0, subsidies: 0 },
    decisionMakers: [
      { name: "Luisa Marín", role: "Administradora única", email: "luisa.marin@lmasesores.com" },
    ],
  },
  {
    id: "orema-economistas",
    razonSocial: "Orema Economistas — Servicios fiscales",
    nif: "B41998877",
    city: "Sevilla",
    province: "Sevilla",
    score: 45,
    grade: "B",
    decisor: "Rafael Orejuela",
    decisorRole: "Socio fundador",
    email: "rafael@oremaeconomistas.com",
    emailConfidence: "high",
    phone: "+34 954 89 17 22",
    domain: "oremaeconomistas.com",
    cnae: "6920",
    sources: ["BORME", "OSM", "PLACSP", "WebContact"],
    compliance: { dpoRegistered: true },
    publicSector: { contracts: 3, subsidies: 0 },
    decisionMakers: [
      { name: "Rafael Orejuela", role: "Socio fundador", email: "rafael@oremaeconomistas.com" },
      { name: "María Ortiz", role: "Socia", email: "maria@oremaeconomistas.com" },
    ],
  },
  {
    id: "asesoria-asfildos",
    razonSocial: "Asesoría Asfildos S.L.",
    nif: "B41234001",
    city: "Sevilla",
    province: "Sevilla",
    score: 22,
    grade: "C",
    phone: "+34 954 22 11 33",
    cnae: "6920",
    sources: ["BORME", "OSM"],
    compliance: { dpoRegistered: false },
    publicSector: { contracts: 0, subsidies: 0 },
    decisionMakers: [],
    webNote: "Sin web detectada en heurístico de dominio",
  },
  {
    id: "olvegest",
    razonSocial: "Olvegest Asesores",
    nif: "B41345678",
    city: "Sevilla",
    province: "Sevilla",
    score: 30,
    grade: "C",
    decisor: "Ana Olvera",
    decisorRole: "Administradora",
    email: "info@olvegest.es",
    emailConfidence: "medium",
    phone: "+34 954 55 22 18",
    domain: "olvegest.es",
    cnae: "6920",
    sources: ["BORME", "WebContact"],
    compliance: { dpoRegistered: false },
    publicSector: { contracts: 0, subsidies: 0 },
    decisionMakers: [
      { name: "Ana Olvera", role: "Administradora", email: "ana@olvegest.es" },
    ],
  },
  {
    id: "san-pablo-asesores",
    razonSocial: "San Pablo Asesores",
    nif: "B41099887",
    city: "Sevilla",
    province: "Sevilla",
    score: 28,
    grade: "C",
    phone: "+34 954 41 09 23",
    domain: "sanpabloasesores.com",
    cnae: "6920",
    sources: ["OSM", "BORME"],
    compliance: { dpoRegistered: false },
    publicSector: { contracts: 0, subsidies: 0 },
    decisionMakers: [],
    webNote: "Email no extraído; añadir manualmente",
  },
  {
    id: "623-servicios-profesionales",
    razonSocial: "623 Servicios Profesionales Independientes",
    nif: "B41887766",
    city: "Dos Hermanas",
    province: "Sevilla",
    score: 18,
    grade: "D",
    cnae: "6920",
    sources: ["OSM"],
    compliance: { dpoRegistered: null },
    publicSector: { contracts: 0, subsidies: 0 },
    decisionMakers: [],
    webNote: "Sin dominio resoluble",
  },
  {
    id: "fernando-del-toro",
    razonSocial: "Asesoría Fernando del Toro",
    city: "Sevilla",
    province: "Sevilla",
    score: 24,
    grade: "C",
    decisor: "Fernando del Toro",
    decisorRole: "Titular",
    phone: "+34 954 76 33 11",
    domain: "mapcarta.com",
    cnae: "6920",
    sources: ["OSM"],
    compliance: { dpoRegistered: null, note: "AEPD respondió js-spa" },
    publicSector: { contracts: 0, subsidies: 0 },
    decisionMakers: [
      { name: "Fernando del Toro", role: "Titular" },
    ],
    webNote: "Dominio resuelto al directorio mapcarta.com; necesita revisión",
  },
  {
    id: "country-properties",
    razonSocial: "Country Properties Andalucía",
    nif: "B41447799",
    city: "Sevilla",
    province: "Sevilla",
    score: 14,
    grade: "D",
    cnae: "6810",
    sources: ["OSM"],
    compliance: { dpoRegistered: null },
    publicSector: { contracts: 0, subsidies: 0 },
    decisionMakers: [],
    webNote: "Coincidencia parcial con sector — revisar CNAE",
  },
  {
    id: "alba-fiscal",
    razonSocial: "Alba Fiscal & Tributario",
    nif: "B41552267",
    city: "Sevilla",
    province: "Sevilla",
    score: 75,
    grade: "A",
    decisor: "Carmen Hernández",
    decisorRole: "Directora",
    email: "carmen.hernandez@albafiscal.es",
    emailConfidence: "high",
    phone: "+34 954 11 22 33",
    domain: "albafiscal.es",
    cnae: "6920",
    sources: ["BORME", "OSM", "Cartociudad", "PLACSP", "WebContact"],
    compliance: { dpoRegistered: true },
    publicSector: { contracts: 5, subsidies: 2 },
    decisionMakers: [
      { name: "Carmen Hernández", role: "Directora", email: "carmen.hernandez@albafiscal.es" },
      { name: "Iván Hernández", role: "Socio", email: "ivan@albafiscal.es" },
    ],
  },
  {
    id: "morback-properties",
    razonSocial: "Morback Properties",
    nif: "B41776655",
    city: "Sevilla",
    province: "Sevilla",
    score: 64,
    grade: "B",
    decisor: "Carmen Hernández",
    decisorRole: "Administradora",
    email: "info@morbackproperties.com",
    emailConfidence: "medium",
    phone: "+34 955 23 78 41",
    domain: "morbackproperties.com",
    cnae: "6810",
    sources: ["BORME", "OSM", "WebContact"],
    compliance: { dpoRegistered: true },
    publicSector: { contracts: 0, subsidies: 0 },
    decisionMakers: [
      { name: "Carmen Hernández", role: "Administradora", email: "info@morbackproperties.com" },
    ],
  },
];
