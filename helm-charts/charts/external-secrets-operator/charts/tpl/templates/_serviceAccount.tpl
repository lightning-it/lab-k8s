{{/*
Create the name of the service account to use.
If not set use "temp-serviceaccount" to ensure 
that templating works and does not break at some point
*/}}
{{- define "tpl.serviceAccountName" -}}
  {{- if .Values.serviceAccount.create }}
    {{- default "temp-serviceaccount" .Values.serviceAccount.name }}
  {{- else }}
    {{- "temp-serviceaccount" }}
  {{- end }}
{{- end }}


{{/*
Create the name of the service account to use.
If not set use "temp-serviceaccount" to ensure 
that templating works and does not break at some point
*/}}
{{- define "tpl.serviceAccount" -}}
  {{- if .create }}
    {{- default "temp-serviceaccount" .name }}
  {{- else }}
    {{- "temp-serviceaccount" }}
  {{- end }}
{{- end }}
