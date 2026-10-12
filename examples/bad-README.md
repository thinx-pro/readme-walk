# tinynotes

[![build](https://img.shields.io/badge/build-passing-green)](https://example.com)

## Install

```bash
$ git clone https://github.com/example/tinynotes
$ cd tinynotes
$ npm install
$ cp env.example .env
```

Set your token in `.env`:

```bash
export TINYNOTES_TOKEN=<your-api-token>
```

## Usage

```
tinynotes add “first note” --dir /Users/alice/notes
```

See [configuration](docs/config.md) and the [FAQ](#faq) for more.

## Development

```bash
make dev
./scripts/seed.sh
docker compose up -d
npm run migrate
npm run test
npm run lint
```
