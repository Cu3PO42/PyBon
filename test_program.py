s1 = 1; n1 = 10
s2 = 0; n2 = 20
sr = 0; nr = 0

if s1 == s2:
    sr = s1
    nr = n1+n2
else:
    if n1 > n2:
        sr = s1
        nr = n1-n2
    else:
        sr = s2
        nr = n2-n1
