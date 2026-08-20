# Emergent Specialization — Slidev deck

This is a versionable, data-backed Slidev research presentation. It reads the
latest completed run artifacts and never performs model inference.

```bash
cd presentation
npm install
npm run data       # refresh presentation/data/presentation-data.json
npm run dev        # browser presentation with presenter mode
```

Build the static web artifact with `npm run build`. Export a PDF backup with
`npm run export`; the command writes `dist/emergent-specialization.pdf`.

The generator selects the newest completed `private-*` run and, when available,
the newest completed `shared-*` run. An incomplete shared run is represented as
pending rather than being interpreted or filled with invented values.
