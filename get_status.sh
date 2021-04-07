#!/bin/bash
python3.9 -c "import core.status_exporter; core.status_exporter.main('$1', '$2')"
