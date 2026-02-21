# kubectl Skills

## timeout
default: 30s
streaming_commands: ["kubectl logs -f", "kubectl get -w"]

## auto_execute
# Read-only operations. Execute immediately, no user prompt.
- kubectl get *
- kubectl describe *
- kubectl logs *
- kubectl top *
- kubectl explain *
- kubectl diff *
- kubectl version
- kubectl cluster-info

## requires_approval
# Mutating operations. Pause, show plan, await yes/no.
- kubectl apply *
- kubectl scale *
- kubectl rollout *
- kubectl edit *
- kubectl patch *
- kubectl label *
- kubectl annotate *
- kubectl exec *

## destructive
# Irreversible operations. Show consequences. Require explicit approval.
- kubectl delete *
- kubectl drain *
- kubectl cordon *
- kubectl uncordon *
- kubectl replace --force *
