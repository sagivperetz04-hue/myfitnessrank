{{- define "web-service.fullname" -}}
{{/*
Defaults to the component name (auth, backend, ...) rather than the release
name: the services reach each other by these fixed DNS names, and under the
core umbrella every alias shares one release name.
*/}}
{{- default .Values.component .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "web-service.labels" -}}
app: myfitnessrank
component: {{ .Values.component }}
{{- /*
The image tag, not .Chart.AppVersion: one generic chart serves every component,
and prod pins tags in its overlay — AppVersion could silently disagree with
what is actually running.
*/}}
version: {{ .Values.image.tag | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "web-service.selectorLabels" -}}
app: myfitnessrank
component: {{ .Values.component }}
{{- end -}}
