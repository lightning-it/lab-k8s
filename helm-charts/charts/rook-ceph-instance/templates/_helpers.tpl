{{- define "global.appsDomain" -}}
{{- if .Values.appsDomain -}}
  {{ .Values.appsDomain }}
{{- else -}}
  {{- printf "%s.%s.%s" .Values.global.ingressSuffix .Values.global.envName .Values.global.baseDomain -}}
{{- end }}
{{- end }}
