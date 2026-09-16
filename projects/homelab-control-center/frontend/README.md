# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.

## Production deployment

The production build is served as static files by the existing Caddy TLS site.
HTTPS clients use the browser origin for API calls, while local HTTP development
continues to use the API port returned by `/config`.

```bash
npm ci
npm run build
release_id=$(git rev-parse --short=12 HEAD)
release_dir=/var/lib/rmt-control-center/frontend/releases/$release_id
sudo install -d -o root -g root -m 0755 "$release_dir"
sudo cp -a dist/. "$release_dir/"
sudo chmod -R a=rX "$release_dir"
sudo ln -sfn "$release_dir" /var/lib/rmt-control-center/frontend/current.next
sudo mv -Tf /var/lib/rmt-control-center/frontend/current.next \
  /var/lib/rmt-control-center/frontend/current
sudo caddy validate --config ../deploy/Caddyfile --adapter caddyfile
sudo install -m 0644 ../deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Releases are immutable directories selected by the atomic `current` symlink.
Rollback repoints that symlink to the preceding release, restores the preceding
Caddyfile from Git when needed, validates it, and reloads Caddy.
The full operational sequence and verification commands are in
`../../../docs/operations/DEPLOY.md`.
